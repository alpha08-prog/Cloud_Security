"""R4 - "examine any attempt of exploiting cross-VM and data leakage" (p.16).

Watches the engine's event stream (through the read-only proxy) and raises a
detection when a workload is created or changed in a way that breaks tenant
isolation. The stream is read in short windows (`until`), so the watcher has a
heartbeat even when nothing happens; XVM-07 checks that heartbeat.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from ..snapshot import L_PLANE, L_SERVICE, L_TENANT, L_WORKLOAD
from .detections import DetectionStore

WINDOW_S = 2.0


def _exec_command(action: str) -> str:
    return action.split(":", 1)[1].strip() if ":" in action else ""


def _healthcheck_command(doc: dict) -> str | None:
    test = ((doc.get("Config") or {}).get("Healthcheck") or {}).get("Test") or []
    if not test or test[0] == "NONE":
        return None
    if test[0] == "CMD":
        return " ".join(test[1:])
    if test[0] == "CMD-SHELL":
        return f"/bin/sh -c {test[1]}"
    return " ".join(test)


class EventWatcher(threading.Thread):
    def __init__(self, client, detections: DetectionStore, policy_getter: Callable, on_change: Callable) -> None:
        super().__init__(name="event-watcher", daemon=True)
        self.client = client
        self.detections = detections
        self.policy = policy_getter
        self.on_change = on_change
        self.heartbeat = 0.0
        self.since = time.time()
        self._containers: dict[str, dict] = {}   # id -> inspect doc (cached at create/start)
        self._networks: dict[str, dict] = {}     # name -> labels
        self._fired: set[tuple[str, str]] = set()
        self.last_error: str | None = None

    def heartbeat_age(self) -> float | None:
        return None if not self.heartbeat else time.time() - self.heartbeat

    def run(self) -> None:
        while True:
            until = time.time() + WINDOW_S
            try:
                for event in self.client.events(since=self.since, until=until, decode=True,
                                                 filters={"type": ["container", "network"]}):
                    self.since = max(self.since, event.get("time", self.since))
                    self.handle(event)
                    self.heartbeat = time.time()
                self.since = max(self.since, until - 0.001)
                self.heartbeat = time.time()
                self.last_error = None
            except Exception as exc:  # reconnect: the proxy may cut long streams
                self.last_error = f"{type(exc).__name__}: {exc}"
                print(f"event watcher error: {self.last_error}", flush=True)
                time.sleep(1)

    # ------------------------------------------------------------------ helpers
    def _inspect(self, cid: str) -> dict | None:
        if cid in self._containers:
            return self._containers[cid]
        try:
            doc = self.client.api.inspect_container(cid)
        except Exception:
            return None
        self._containers[cid] = doc
        return doc

    def _network_labels(self, name: str) -> dict:
        if name not in self._networks:
            try:
                self._networks[name] = self.client.api.inspect_network(name).get("Labels") or {}
            except Exception:
                return {}
        return self._networks[name]

    def _fire(self, rule: str, cid: str, attrs: dict, event_ns: int, message: str, evidence: dict | None = None):
        if (rule, cid) in self._fired and rule not in ("DET-01", "DET-06"):
            return
        self._fired.add((rule, cid))
        self.detections.raise_(rule, tenant=attrs.get(L_TENANT), workload_id=attrs.get(L_WORKLOAD),
                               service=attrs.get(L_SERVICE) or attrs.get("name"), event_time_ns=event_ns,
                               message=message, evidence=evidence)

    def _excepted(self, attrs: dict, check_id: str) -> bool:
        policy = self.policy()
        service = attrs.get(L_SERVICE) or ""
        return bool(policy and policy.exception_for(service, check_id))

    # ------------------------------------------------------------------ rules
    def handle(self, event: dict) -> None:
        etype, action = event.get("Type"), event.get("Action", "")
        actor = event.get("Actor") or {}
        attrs = actor.get("Attributes") or {}
        event_ns = int(event.get("timeNano") or time.time_ns())
        if etype == "container":
            self._container_event(action, actor.get("ID", ""), attrs, event_ns)
        elif etype == "network" and action == "connect":
            self._network_connect(attrs, event_ns)

    def _container_event(self, action: str, cid: str, attrs: dict, event_ns: int) -> None:
        verb = action.split(":", 1)[0]
        plane = attrs.get(L_PLANE) or "tenant"
        if verb in ("create", "start"):
            doc = self._inspect(cid)
            if verb == "start":
                self.on_change()
            if doc is None or plane == "operator":
                return
            labels = (doc.get("Config") or {}).get("Labels") or {}
            attrs = {**labels, "name": doc.get("Name", "").lstrip("/")}
            hc = doc.get("HostConfig") or {}
            name = attrs.get(L_SERVICE) or attrs["name"]
            if hc.get("Privileged"):
                self._fire("DET-02", cid, attrs, event_ns, f"{name} started with --privileged")
            sockets = [m.get("Source") for m in doc.get("Mounts") or []
                       if "docker.sock" in (m.get("Source") or "") or "containerd.sock" in (m.get("Source") or "")]
            if sockets and not self._excepted(attrs, "HV-01"):
                self._fire("DET-03", cid, attrs, event_ns, f"{name} mounts the engine socket",
                           {"mounts": sockets})
            host_ns = [k for k in ("PidMode", "NetworkMode", "IpcMode", "UTSMode") if hc.get(k) == "host"]
            if host_ns:
                self._fire("DET-04", cid, attrs, event_ns, f"{name} joins host namespaces: {', '.join(host_ns)}",
                           {"namespaces": host_ns})
            if not labels.get(L_PLANE) or not labels.get(L_WORKLOAD):
                self._fire("DET-05", cid, attrs, event_ns, f"{name} started without an identity",
                           {"image": (doc.get("Config") or {}).get("Image")})
        elif verb == "exec_create":
            if plane != "tenant":
                return
            doc = self._inspect(cid)
            command = _exec_command(action)
            if doc is not None and command and command == _healthcheck_command(doc):
                return  # the engine's own healthcheck, not a person
            name = attrs.get(L_SERVICE) or attrs.get("name")
            self._fire("DET-01", cid, attrs, event_ns, f"exec into {name}: {command[:80]}",
                       {"command": command[:200]})
        elif verb == "oom":
            self._fire("DET-09", cid, attrs, event_ns, f"{attrs.get(L_SERVICE) or attrs.get('name')} hit its "
                                                       f"memory limit")
        elif verb in ("die", "destroy"):
            if verb == "destroy":
                self._containers.pop(cid, None)
            self.on_change()

    def _network_connect(self, attrs: dict, event_ns: int) -> None:
        cid, net = attrs.get("container", ""), attrs.get("name", "")
        if net in ("none", "host"):  # no network / host namespace (DET-04 covers host)
            return
        doc = self._inspect(cid)
        if doc is None:
            return
        clabels = (doc.get("Config") or {}).get("Labels") or {}
        plane = clabels.get(L_PLANE) or "tenant"
        if plane != "tenant":
            return
        nlabels = self._network_labels(net)
        owner = nlabels.get(L_TENANT)
        mine = clabels.get(L_TENANT)
        self.on_change()
        if owner and owner == mine:
            return
        where = f"tenant {owner}'s network" if owner else f"{nlabels.get(L_PLANE) or 'unowned'} network"
        name = clabels.get(L_SERVICE) or doc.get("Name", "").lstrip("/")
        self._fire("DET-06", cid, {**clabels, "name": name}, event_ns, f"{name} (tenant {mine}) attached to {where} "
                   f"{net.removeprefix('isolab_')}", {"network": net.removeprefix("isolab_"), "networkOwner": owner})
