"""Fetch the pre-registered OpenAlex samples (one seeded random sample per era)."""

from __future__ import annotations

import os
import urllib.parse

from isolab import util

from . import config, net, snapshot


def filter_string(era: str) -> str:
    return ",".join([
        f"title_and_abstract.search:{config.SEARCH}",
        f"publication_year:{era}",
        "has_abstract:true",
        "language:en",
        "type:" + "|".join(config.TYPES),
        "is_retracted:false",
        "is_paratext:false",
    ])


def _url(params: dict) -> str:
    mailto = os.environ.get("OPENALEX_MAILTO")  # optional; never written to disk
    if mailto:
        params = {**params, "mailto": mailto}
    return f"{config.OPENALEX}?{urllib.parse.urlencode(params)}"


def _public(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k not in ("mailto", "api_key")]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))


def fetch(force: bool = False) -> dict:
    manifest_path = config.CORPUS / "manifest.json"
    if manifest_path.exists() and not force:
        util.ok(f"corpus snapshot already present ({manifest_path.relative_to(util.REPO)}); use --force to refetch")
        return util.read_json(manifest_path)
    manifest = {"source": "OpenAlex works API (CC0)", "search": config.SEARCH, "types": config.TYPES,
                "samplePerEra": config.SAMPLE_PER_ERA, "retrievedAt": util.utc_now(), "eras": {}}
    for era, seed in config.ERAS.items():
        flt = filter_string(era)
        count_doc = net.get_json(_url({"filter": flt, "per-page": 1}), cache_dir=None, min_interval=1.5)
        population = count_doc["meta"]["count"]
        records: list[dict] = []
        pages = -(-config.SAMPLE_PER_ERA // config.PAGE_SIZE)
        for page in range(1, pages + 1):
            url = _url({"filter": flt, "sample": config.SAMPLE_PER_ERA, "seed": seed, "per-page": config.PAGE_SIZE,
                        "page": page, "select": ",".join(config.SELECT)})
            doc = net.get_json(url, cache_dir=config.CACHE / "openalex" / era, min_interval=1.5)
            records.extend(doc.get("results", []))
            util.info(f"{era}: page {page}/{pages} ({len(records)} records)")
        sha = snapshot.write_jsonl_gz(config.CORPUS / f"openalex-{era}.jsonl.gz", records)
        manifest["eras"][era] = {
            "seed": seed, "population": population, "records": len(records),
            "uniqueIds": len({r["id"] for r in records}), "sha256": sha,
            "exampleUrl": _public(_url({"filter": flt, "sample": config.SAMPLE_PER_ERA, "seed": seed,
                                        "per-page": config.PAGE_SIZE, "page": 1})),
        }
        unique = manifest["eras"][era]["uniqueIds"]
        util.ok(f"{era}: population {population:,}, sampled {len(records)} ({unique} unique)")
    util.write_json(manifest_path, manifest)
    return manifest
