"""The 30 static checks, each tied back to the paper.

Every check names
  * one of Figure 11's five virtualization sub-issues (its axis),
  * the requirement(s) from the paper's future-work brief (p.16) it serves (R1-R4),
  * node ids from the paper's taxonomy (Figures 2-4),
  * the CSA Top Threats / CSA Guidance domains / ENISA risk classes / NIST roles it
    relates to (Tables 1-2, pp.11-13).
The check logic lives in cloudaudit.checks; this module is data only, so it can
also be exported as documentation (docs/checks.md) and embedded in each report.
"""

from __future__ import annotations

from .models import CheckSpec, Frameworks

V = "architecture/virtualization"
NET = "architecture/network-security"
IF = "architecture/interfaces"
SVC = "compliance/service"
PROV = "compliance/provider"
DATA = "privacy/data-security"
LEGAL = "privacy/legal-issues"


def fw(threats: list[int], domains: list[str], enisa: list[str], nist: list[str]) -> Frameworks:
    return Frameworks(csa_top_threats=threats, csa_domains=domains, enisa=enisa, nist=nist)


def spec(id: str, title: str, axis: str, req: list[str], severity: str, scope: str, taxonomy: list[str],
         frameworks: Frameworks, description: str, remediation: str, platform_notes: str | None = None) -> CheckSpec:
    return CheckSpec(id=id, title=title, axis=axis, requirements=req, severity=severity, scope=scope,
                     taxonomy=taxonomy, frameworks=frameworks, description=description, remediation=remediation,
                     platform_notes=platform_notes)


CATALOGUE: list[CheckSpec] = [
    # ------------------------------------------------------------------ isolation
    spec("ISO-01", "Workload is not privileged", "isolation", ["R2"], "critical", "container",
         [f"{V}/isolation/logical-isolation", f"{LEGAL}/provider-privilege/privilege-escalation"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "A privileged container has every capability and direct access to host devices; its isolation from "
         "the host and from other tenants is nominal.",
         "Remove `privileged: true`; grant only the specific capability a workload needs, if any."),
    spec("ISO-02", "Capabilities dropped to the minimum", "isolation", ["R2"], "high", "container",
         [f"{V}/isolation/logical-isolation", f"{LEGAL}/provider-privilege/privilege-escalation"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider", "consumer"]),
         "Linux capabilities split root's power into pieces. Tenants should drop all of them and add back "
         "only what the policy allows.",
         "Set `cap_drop: [ALL]` and keep `cap_add` within the policy allowlist."),
    spec("ISO-03", "Syscall filter on, privilege gain blocked", "isolation", ["R2"], "high", "container",
         [f"{V}/isolation/logical-isolation"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "The engine's default seccomp profile blocks dangerous syscalls (shrinking the shared-kernel attack "
         "surface); no-new-privileges stops setuid binaries from gaining privileges.",
         "Never run with `seccomp=unconfined`; add `no-new-privileges:true` to `security_opt`."),
    spec("ISO-04", "Runs as a non-root user", "isolation", ["R2"], "medium", "container",
         [f"{LEGAL}/provider-privilege/privilege-escalation"],
         fw([4], ["identity-and-access-management"], ["technical"], ["consumer"]),
         "Root inside a container is root on the shared kernel for anything that escapes the namespace.",
         "Set a numeric non-root `user:` (e.g. 10001) or a non-root USER in the image."),
    spec("ISO-05", "Private process and hostname namespaces", "isolation", ["R2"], "critical", "container",
         [f"{V}/isolation/logical-isolation", f"{V}/vm-identification/multiple-processes"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "Sharing the host PID or UTS namespace lets a workload see and signal every process on the host.",
         "Remove `pid: host` and `uts: host`."),
    spec("ISO-06", "CPU, memory and process limits set", "isolation", ["R2"], "high", "container",
         [f"{V}/isolation/physical-isolation", f"{NET}/firewalling/dos-prevention", f"{SVC}/sla/availability"],
         fw([1, 4], ["virtualization", "traditional-security-business-continuity-and-disaster-recovery"],
            ["technical"], ["cloud-provider"]),
         "Without limits one tenant can exhaust CPU, memory or PIDs for everyone on the host (the noisy "
         "neighbour of experiment E1). Swap must be capped too, or memory limits leak into shared swap.",
         "Set `cpus`, `mem_limit` equal to `memswap_limit`, and `pids_limit`."),
    spec("ISO-07", "Dedicated CPU sets per tenant", "isolation", ["R2"], "high", "fleet",
         [f"{V}/isolation/physical-isolation"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "The paper asks for 'adequate separation of dedicated resources'. Each tenant gets its own CPUs; no "
         "two tenants' CPU sets overlap.",
         "Give every tenant a `cpuset`; generate them with `lab.py cpus` so they never overlap."),
    # ------------------------------------------------------------------ hypervisor (engine + shared kernel)
    spec("HV-01", "Engine API not exposed to workloads", "hypervisor-vulnerabilities", ["R2"], "critical",
         "container",
         [f"{V}/hypervisor-vulnerabilities/virtualization", f"{IF}/administrative-interface/vm-management"],
         fw([2, 3], ["virtualization", "identity-and-access-management"], ["technical"], ["cloud-provider"]),
         "The container engine is this testbed's hypervisor. Whoever holds its socket controls every "
         "workload on the host.",
         "Never mount docker/containerd sockets into workloads; give monitoring a read-only API proxy instead.",
         "The provider's socket-proxy is the single documented exception."),
    spec("HV-02", "Engine and kernel at the patch baseline", "hypervisor-vulnerabilities", ["R3"], "medium",
         "host",
         [f"{V}/hypervisor-vulnerabilities/virtualization", f"{V}/hypervisor-vulnerabilities/proprietary-solutions"],
         fw([4], ["virtualization", "data-center-operations"], ["technical"], ["cloud-provider"]),
         "The shared kernel and engine are the 'hypervisor' every tenant depends on; they must be at or above "
         "the policy's minimum versions.",
         "Upgrade Docker Engine / the host kernel to the versions in policy.yaml."),
    spec("HV-03", "CPU vulnerability mitigations active", "hypervisor-vulnerabilities", ["R3"], "high", "host",
         [f"{V}/hypervisor-vulnerabilities/virtualization", f"{V}/cross-vm-attacks/cryptographic-key-stealing"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "The kernel reports, per known CPU flaw, whether it is mitigated. A 'Vulnerable' entry is a "
         "shared-hardware weakness every tenant inherits and none of them can fix.",
         "Update host microcode/firmware and the kernel; this is the provider's responsibility.",
         "Virtualised hosts (WSL2, cloud VMs) cannot load microcode themselves: expect waivers there."),
    spec("HV-04", "User-namespace isolation enabled", "hypervisor-vulnerabilities", ["R2"], "medium", "host",
         [f"{LEGAL}/provider-privilege/privilege-escalation", f"{V}/isolation/logical-isolation"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "With user namespaces (userns-remap or rootless mode) root in a container maps to an unprivileged "
         "user on the host, so an escape lands without privileges.",
         "Enable `userns-remap` in daemon.json or run the engine rootless.",
         "Docker Desktop offers this only with Enhanced Container Isolation (Business tier)."),
    spec("HV-05", "Mandatory access control profile applied", "hypervisor-vulnerabilities", ["R2"], "medium",
         "container",
         [f"{V}/hypervisor-vulnerabilities/virtualization"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "AppArmor/SELinux confine what a process may touch even as root. Applies where the host supports it.",
         "Keep the engine's default AppArmor profile (`docker-default`); never set `apparmor=unconfined`.",
         "Skipped on hosts without AppArmor or SELinux (e.g. Docker Desktop)."),
    spec("HV-06", "Host kernel hardening settings", "hypervisor-vulnerabilities", ["R3"], "medium", "host",
         [f"{V}/hypervisor-vulnerabilities/virtualization", f"{NET}/security-configuration/systems"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "Kernel settings that hide kernel addresses and logs from unprivileged users and restrict eBPF and "
         "performance counters on the shared kernel.",
         "Set the sysctls listed in policy.yaml (lab.py applies them when bringing up the hardened profile)."),
    # ------------------------------------------------------------------ data leakage
    spec("DL-01", "No sensitive or writable host mounts", "data-leakage", ["R2"], "high", "container",
         [f"{V}/data-leakage/confidentiality", f"{V}/data-leakage/integrity"],
         fw([5], ["information-management-and-data-security", "virtualization"], ["technical"],
            ["cloud-provider"]),
         "Bind-mounting host paths into a tenant exposes host or other tenants' data and, if writable, lets "
         "the tenant alter it.",
         "Use named volumes owned by the tenant; never bind host system paths."),
    spec("DL-02", "No storage shared between tenants", "data-leakage", ["R2"], "high", "fleet",
         [f"{V}/data-leakage/confidentiality", f"{NET}/transfer-security/resource-sharing"],
         fw([5, 4], ["information-management-and-data-security"], ["technical"], ["cloud-provider"]),
         "A volume mounted by two tenants is a direct data channel between them.",
         "Give each tenant its own volume, labelled with its tenant id."),
    spec("DL-03", "No shared IPC namespace", "data-leakage", ["R2"], "high", "container",
         [f"{V}/data-leakage/confidentiality"],
         fw([4, 5], ["virtualization"], ["technical"], ["cloud-provider"]),
         "Sharing the host's (or another tenant's) IPC namespace exposes shared memory segments and queues.",
         "Remove `ipc: host`; never join another tenant's IPC namespace."),
    spec("DL-04", "Read-only root filesystem", "data-leakage", ["R2"], "medium", "container",
         [f"{V}/data-leakage/integrity"],
         fw([5], ["application-security"], ["technical"], ["consumer"]),
         "An immutable root filesystem stops a compromised workload from altering its own code or planting "
         "files; writable state lives only in declared volumes and tmpfs.",
         "Set `read_only: true` and mount a small tmpfs for /tmp."),
    spec("DL-05", "No secrets in environment variables", "data-leakage", ["R4"], "medium", "container",
         [f"{DATA}/cryptography/sensitive-data", f"{V}/data-leakage/confidentiality"],
         fw([5], ["encryption-and-key-management"], ["technical"], ["consumer"]),
         "Environment variables leak through `inspect`, crash dumps and child processes. Only variable names "
         "are checked and reported, never their values.",
         "Pass secrets as files (Compose secrets) and read them at runtime."),
    # ------------------------------------------------------------------ cross-VM (cross-tenant)
    spec("XVM-01", "No network shared by two tenants", "cross-vm-attacks", ["R2"], "critical", "fleet",
         [f"{NET}/firewalling/vm-isolation", f"{V}/cross-vm-attacks/vm-placement-overlapping-attacks"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "Tenants on a common network can reach each other directly, so one compromised tenant can attack "
         "the others.",
         "Put each tenant on its own network; route any necessary traffic through a provider gateway."),
    spec("XVM-02", "Tenant networks are internal", "cross-vm-attacks", ["R2"], "medium", "network",
         [f"{NET}/firewalling/filtering", f"{V}/data-leakage/confidentiality"],
         fw([5, 4], ["traditional-security-business-continuity-and-disaster-recovery"], ["technical"],
            ["cloud-provider"]),
         "Tenant networks without egress cannot exfiltrate data or reach the default bridge where other "
         "workloads may live.",
         "Mark tenant networks `internal: true`; never attach tenants to the default `bridge`."),
    spec("XVM-03", "No host network namespace", "cross-vm-attacks", ["R2"], "critical", "container",
         [f"{NET}/firewalling/vm-isolation"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "With the host's network stack a workload can reach every service on the host and every tenant.",
         "Remove `network_mode: host`."),
    spec("XVM-04", "Tenants publish no host ports", "cross-vm-attacks", ["R2"], "medium", "container",
         [f"{NET}/firewalling/filtering"],
         fw([6, 4], ["traditional-security-business-continuity-and-disaster-recovery"], ["technical"],
            ["cloud-provider"]),
         "A published port is a path around network segmentation (other tenants can reach it via the host) "
         "and, on 0.0.0.0, exposes the tenant to the LAN.",
         "Do not publish tenant ports; expose services through the provider's ingress."),
    spec("XVM-05", "No physical core shared by two tenants", "cross-vm-attacks", ["R2"], "high", "fleet",
         [f"{V}/isolation/physical-isolation", f"{V}/cross-vm-attacks/cryptographic-key-stealing"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "SMT (hyper-threading) siblings share a core's caches and execution units. Tenants that share a "
         "physical core are not separated in hardware, which is what cross-VM attacks rely on.",
         "Plan CPU sets on physical-core boundaries (lab.py cpus), or disable SMT for sensitive workloads.",
         "Inside a VM the core topology is virtual, so this check is indicative there."),
    spec("XVM-06", "Memory deduplication (KSM) off", "cross-vm-attacks", ["R2"], "medium", "host",
         [f"{V}/isolation/physical-isolation", f"{V}/cross-vm-attacks/vm-placement-overlapping-attacks"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "Kernel same-page merging makes identical memory pages of different tenants physically shared.",
         "Keep /sys/kernel/mm/ksm/run at 0 on multi-tenant hosts."),
    spec("XVM-07", "Cross-tenant tripwires armed", "cross-vm-attacks", ["R4"], "high", "self",
         [f"{V}/cross-vm-attacks", f"{SVC}/audit/security-assessments"],
         fw([3, 4], ["incident-response-notification-and-remediation"], ["technical"], ["auditor"]),
         "The paper asks solutions to 'examine any attempt of exploiting cross-VM and data leakage'. That "
         "needs live detection: the engine-event watcher running, the canary healthy, alert rules loaded.",
         "Keep the auditor service, the canary and Prometheus rules running."),
    # ------------------------------------------------------------------ VM identification
    spec("ID-01", "Every workload carries an identity", "vm-identification", ["R1"], "high", "container",
         [f"{V}/vm-identification/multiple-users", f"{V}/vm-identification/multiple-processes",
          f"{PROV}/data-control/configurations"],
         fw([7], ["governance-and-risk-management"], ["policy-organizational"], ["cloud-provider", "consumer"]),
         "The paper's first requirement: 'virtual machine identification'. Each workload declares its plane, "
         "tenant, owner and a unique workload id.",
         "Add the io.isolab.* identity labels (see policy.yaml)."),
    spec("ID-02", "No unattributed workloads on the host", "vm-identification", ["R1"], "high", "fleet",
         [f"{V}/vm-identification/multiple-resources", f"{PROV}/security-control/loss-of-control-over-policies"],
         fw([7, 1], ["governance-and-risk-management"], ["policy-organizational"], ["auditor"]),
         "Anything running on the host without an identity is outside every control (CSA's 'unknown risk "
         "profile').",
         "Label or remove the workload; list sanctioned exceptions in policy.yaml."),
    spec("ID-03", "Identity matches network and storage placement", "vm-identification", ["R1"], "high",
         "container",
         [f"{V}/vm-identification/multiple-resources", f"{IF}/authentication/multi-tenancy"],
         fw([4], ["virtualization"], ["technical"], ["cloud-provider"]),
         "A workload labelled as tenant X must only be attached to tenant X's networks and volumes.",
         "Label networks and volumes with their tenant and attach workloads only to their own."),
    spec("ID-04", "Image provenance recorded", "vm-identification", ["R1"], "medium", "container",
         [f"{V}/vm-identification/multiple-resources", f"{SVC}/audit/transparency"],
         fw([7], ["application-security"], ["technical"], ["consumer"]),
         "Knowing exactly what runs: images are pinned by digest, or built from a digest-pinned base and "
         "labelled with their source revision.",
         "Pin `image:` by @sha256 digest; build from pinned bases with OCI revision/base labels."),
    spec("ID-05", "Every tenant continuously observed", "vm-identification", ["R1", "R3"], "high", "self",
         [f"{V}/vm-identification/multiple-processes", f"{SVC}/audit/transparency"],
         fw([7], ["compliance-and-audit"], ["technical"], ["auditor"]),
         "The paper asks for 'constant observation of shared' resources: every tenant must have fresh usage "
         "and pressure samples.",
         "Keep the auditor running; make sure its cgroup mount is present so pressure (PSI) is readable."),
]

BY_ID: dict[str, CheckSpec] = {c.id: c for c in CATALOGUE}

assert len(BY_ID) == len(CATALOGUE), "duplicate check id"


def to_markdown() -> str:
    """docs/checks.md - generated, do not edit by hand."""
    lines = [
        "# IsoLab check catalogue",
        "",
        "Generated by `cloudaudit catalogue --format md`. Do not edit by hand.",
        "",
        "Each check maps to one of Figure 11's five virtualization sub-issues (its *axis*), to the",
        "requirements R1-R4 from the paper's future-work brief (p.16), and to nodes of the paper's taxonomy",
        "(Figures 2-4).",
        "",
        "| Id | Check | Axis | Req | Severity | Scope | Taxonomy |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in CATALOGUE:
        lines.append(f"| {c.id} | {c.title} | {c.axis} | {', '.join(c.requirements)} | {c.severity} | {c.scope} | "
                     f"{'<br>'.join(f'`{t}`' for t in c.taxonomy)} |")
    lines += ["", "## Details", ""]
    for c in CATALOGUE:
        f = c.frameworks
        lines += [
            f"### {c.id} {c.title}",
            "",
            c.description,
            "",
            f"- **Remediation:** {c.remediation}",
            f"- **CSA Top Threats:** {', '.join(map(str, f.csa_top_threats))} · **CSA domains:** "
            f"{', '.join(f.csa_domains)} · **ENISA:** {', '.join(f.enisa)} · **NIST:** {', '.join(f.nist)}",
        ]
        if c.platform_notes:
            lines.append(f"- **Platform notes:** {c.platform_notes}")
        lines.append("")
    return "\n".join(lines)
