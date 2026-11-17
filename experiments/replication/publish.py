"""Build results/published/replication.json (docs/replication.md §7) from the analysis outputs.

Rebuilt abstracts are never published: only counts, shares, intervals and metrics.
"""

from __future__ import annotations

from isolab import util

from . import analysis, config, freeze

ERA_LABELS = {"2013-2017": ("2013–2017", 2013, 2017), "2018-2022": ("2018–2022", 2018, 2022),
              "2023-2026": ("2023–2026", 2023, 2026)}

UNIT = ("one concern entry per (abstract, Figure-5 sub-category); a solution-type abstract also adds one "
        "solution entry per sub-category in its solution window; share = entries / all entries of that kind, "
        "gap = solution share - concern share (percentage points)")
SOLUTION_RULE = ("rule B (scoped): sub-categories hit in the title or from the first contribution sentence on; "
                 "if none, every hit. Figure-11 sub-issues share the same window")
DEVIATIONS = [
    "D1 (CVE supplement only): Linux-kernel crash dumps are removed from CVE descriptions before classification; "
    "the literature replication is unaffected",
]
LIMITATIONS = [
    "Titles and abstracts only, not full texts as in the 2012 survey.",
    "An academic corpus (OpenAlex); the survey mixed academic and industry sources. OpenAlex lacks most "
    "Elsevier abstracts, so the publisher mix is skewed.",
    "Keyword rules, not manual reading: recall differs by category (technical vocabulary is found more reliably "
    "than diffuse legal language); per-category precision and recall are reported.",
    "One annotator, who is also an author; mitigated by blinding, frozen guidelines and hidden repeats.",
    "Figures 5, 7 and 11 of the survey are read from the charts (approximate); Figures 6 and 8 are exact.",
    "Virtualization counts are small, so its intervals are wide; HR4 is tested on pooled data for that reason.",
]


def build(*, flows_doc: dict, analysis_doc: dict, validation: dict, dev: dict, cve_doc: dict) -> dict:
    frozen = freeze.check()
    corpus_manifest = util.read_json(config.CORPUS / "manifest.json")
    nvd_manifest = util.read_json(config.NVD / "manifest.json")
    eras = list(config.ERAS)
    gate = validation["weighted"]["validityGate"]
    hyps = analysis.hypotheses(analysis_doc["stats"], gate, eras)
    return {
        "kind": "replication",
        "schemaVersion": "1.0.0",
        "generatedAt": util.utc_now(),
        "protocol": {
            "document": "docs/replication.md",
            "query": config.SEARCH,
            "eras": [{"id": e, "label": ERA_LABELS[e][0], "seed": config.ERAS[e], "firstYear": ERA_LABELS[e][1],
                      "lastYear": ERA_LABELS[e][2], "partial": e == eras[-1]} for e in eras],
            "samplePerEra": config.SAMPLE_PER_ERA,
            "frozenAt": frozen["frozenAt"],
            "rulesSha256": frozen["files"],
            "corpusSha256": {e: corpus_manifest["eras"][e]["sha256"] for e in eras},
            "nvdSha256": nvd_manifest["sha256"],
            "bootstrapB": analysis_doc["bootstrap"]["b"],
            "bootstrapSeed": analysis_doc["bootstrap"]["seed"],
            "unit": UNIT,
            "solutionRule": SOLUTION_RULE,
            "deviations": DEVIATIONS,
        },
        "hypotheses": hyps,
        "validityGateMet": gate["met"],
        "flow": flows_doc,
        "categories": analysis_doc["categories"],
        "subcategories": analysis_doc["subcategories"],
        "axes": analysis_doc["axes"],
        "robustness": analysis_doc["robustness"],
        "validation": {**{k: validation[k] for k in ("n", "screens", "repeats", "unsure", "completedAt",
                                                    "weighted", "unweighted", "selfAgreement")},
                       "dev": dev},
        "publishers": analysis_doc["publishers"],
        "cve": cve_doc,
        "limitations": LIMITATIONS,
    }


def write(doc: dict) -> None:
    dest = util.PUBLISHED
    util.write_json(dest / "replication.json", doc)
    manifest_path = dest / "manifest.json"
    manifest = util.read_json(manifest_path) if manifest_path.exists() else {"files": []}
    manifest["files"] = sorted(set(manifest.get("files", [])) | {"replication.json"})
    manifest["replicationGeneratedAt"] = doc["generatedAt"]
    util.write_json(manifest_path, manifest)
