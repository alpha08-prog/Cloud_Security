"""Fetch the NVD CVE supplement: candidate CVEs for the virtualization stack, plus the
total number of CVEs published per quarter (to normalise counts per 10,000 CVEs)."""

from __future__ import annotations

import datetime as dt
import os
import urllib.parse

from isolab import util

from . import config, net, snapshot


def _get(params: dict) -> dict:
    headers = {"apiKey": os.environ["NVD_API_KEY"]} if os.environ.get("NVD_API_KEY") else None
    url = f"{config.NVD_API}?{urllib.parse.urlencode(params)}"
    interval = 0.7 if headers else config.NVD_SLEEP_S
    return net.get_json(url, cache_dir=config.CACHE / "nvd", min_interval=interval, headers=headers)


def _query(params: dict) -> list[dict]:
    items, start = [], 0
    while True:
        doc = _get({**params, "noRejected": "", "resultsPerPage": 2000, "startIndex": start})
        items.extend(doc.get("vulnerabilities", []))
        start += doc.get("resultsPerPage", 0)
        if not doc.get("resultsPerPage") or start >= doc.get("totalResults", 0):
            return items


def trim(item: dict) -> dict:
    cve = item["cve"]
    desc = next((d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), "")
    cwes = sorted({d["value"] for w in cve.get("weaknesses", []) for d in w.get("description", [])
                   if d.get("value", "").startswith("CWE-")})
    score = severity = None
    metrics = cve.get("metrics", {})
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if metrics.get(key):
            data = metrics[key][0].get("cvssData", {})
            score = data.get("baseScore")
            severity = data.get("baseSeverity") or metrics[key][0].get("baseSeverity")
            break
    return {"id": cve["id"], "published": cve.get("published"), "lastModified": cve.get("lastModified"),
            "vulnStatus": cve.get("vulnStatus"), "description": desc, "cwe": cwes,
            "cvssScore": score, "cvssSeverity": severity}


def quarters(first_year: int, until: dt.date) -> list[tuple[dt.date, dt.date]]:
    out = []
    for year in range(first_year, until.year + 1):
        for q in range(4):
            start = dt.date(year, 3 * q + 1, 1)
            if start > until:
                return out
            following = dt.date(year + 1, 1, 1) if q == 3 else dt.date(year, 3 * q + 4, 1)
            out.append((start, min(following - dt.timedelta(days=1), until)))
    return out


def fetch(force: bool = False) -> dict:
    manifest_path = config.NVD / "manifest.json"
    if manifest_path.exists() and not force:
        util.ok(f"NVD snapshot already present ({manifest_path.relative_to(util.REPO)}); use --force to refetch")
        return util.read_json(manifest_path)
    found: dict[str, dict] = {}
    queries = [("keyword", t, {"keywordSearch": t}) for t in config.NVD_PRODUCT_TERMS]
    queries += [("phrase", p, {"keywordSearch": p, "keywordExactMatch": ""}) for p in config.NVD_PHRASES]
    for kind, term, params in queries:
        items = _query(params)
        for item in items:
            rec = found.setdefault(item["cve"]["id"], {**trim(item), "matchedBy": []})
            rec["matchedBy"].append(term)
        util.info(f"NVD {kind} '{term}': {len(items)} CVEs ({len(found)} unique so far)")
    records = sorted(found.values(), key=lambda r: r["id"])
    for r in records:
        r["matchedBy"] = sorted(set(r["matchedBy"]))
    sha = snapshot.write_jsonl_gz(config.NVD / "candidates.jsonl.gz", records)

    today = dt.date.today()
    totals = []
    for start, end in quarters(config.NVD_FIRST_YEAR, today):
        doc = _get({"pubStartDate": f"{start.isoformat()}T00:00:00.000",
                    "pubEndDate": f"{end.isoformat()}T23:59:59.999",
                    "noRejected": "", "resultsPerPage": 1})
        totals.append({"start": start.isoformat(), "end": end.isoformat(), "total": doc.get("totalResults", 0)})
        util.info(f"NVD total {start}..{end}: {totals[-1]['total']}")
    util.write_json(config.NVD / "totals.json", totals)
    manifest = {"source": "NVD CVE API 2.0 (public domain)", "retrievedAt": util.utc_now(),
                "productTerms": config.NVD_PRODUCT_TERMS, "phrases": config.NVD_PHRASES, "noRejected": True,
                "candidates": len(records), "sha256": sha, "firstYear": config.NVD_FIRST_YEAR}
    util.write_json(manifest_path, manifest)
    util.ok(f"NVD: {len(records)} candidate CVEs, {len(totals)} quarterly totals")
    return manifest
