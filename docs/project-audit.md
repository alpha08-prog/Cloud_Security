# Project completion audit

**Current update, November 11:** see the research-refinement section at the end and
[the revised demo](research/DEMO.md). The hardened stack now starts successfully; fresh E2/E3
smoke and audit checks pass with the documented waivers. New integrity enforcement and E4/E5
experiments are implemented. The following November 9 findings retain their historical date.

Audit date: 9 November 2026. Scope: all repository components, the selected local 18-page PDF, source requirements, published experimental evidence, tests, and the 20 + 15 mark rubric. This is an evidence assessment, not a predicted mark.

## Overall finding

The core implementation and experimental evaluation are substantially complete. A research manuscript and PDF have now been added, and two evidence-validation defects have been corrected. The separate literature replication remains incomplete. A fresh live run of the final revision has not been performed because Docker's Linux engine is not running. Historical measurements are explicitly preserved as historical evidence.

## Rubric mapping

| Assessment component | Evidence | Status |
|---|---|---|
| Relevant article selection | Gonzalez et al., Journal of Cloud Computing 1:11, 2012; local source PDF reviewed, including page 16 | Complete, subject to instructor accepting implementation of a survey's future-work requirements |
| Technical contribution, part of 20 marks | 30 mapped checks; two configuration profiles; resource planner; observation; nine runtime rules; canary; policy gates; schema and SARIF pipeline | Implemented; integrated engineering contribution, no claim of a new security algorithm |
| Research paper writing, part of 20 marks | `research/IsoLab_IEEE.tex` and `research/IsoLab_Research_Paper.pdf` | IEEEtran conference manuscript with named authors, abstract, questions, related work, threat model, method, results, discussion, limitations, conclusion, references |
| Proposed approach implementation, part of 15 marks | R1 identification, R2 resource separation, R3 observation, R4 activity examination mapped to source page 16 | Implemented as a container adaptation; VM exploits and leakage resistance are not established |
| Experimental evaluation, part of 15 marks | E1 twelve measured runs; E2 twelve probes plus three controls per profile; E3 eight triggers per profile with profile-specific expectations | Committed full-run evidence exists; independently reanalysed |
| Result analysis, part of 15 marks | Independent arithmetic, descriptive run ranges, detection small-sample caveats, hypothesis outcomes, limitations | Completed in manuscript and generated evidence file |

## Repository review

| Area | Review finding |
|---|---|
| `auditor/` | Snapshot-based checks, scores, waivers, policy gate, events, monitoring, reports, schemas and tests are implemented. Two waiver approval fields remain pending owner review. DET-09 OOM exists but has no E3 trigger. |
| `testbed/` | Provider and tenant planes; insecure and hardened overlays; tenant images; benign probes; resource controls and identity labels are present. Container isolation differs from hypervisor isolation. |
| `monitor/` | Prometheus scrape and alert configuration plus provisioned Grafana dashboard are present. Live operation was not reverified in this audit. |
| `experiments/isolab/` and `scripts/lab.py` | Orchestration, E1-E3, publication, gates and topology planning exist. Evidence gate defects were fixed and regression-tested. |
| `experiments/replication/` and `replication/` | Corpus and NVD hashes and frozen classifier match. Blind annotation is 0/110 screens. No `results/published/replication.json`; hypotheses HR1-HR5 cannot be reported as completed results. Frozen rules and blind sample were not modified or exposed. |
| `results/published/` and `schemas/` | All seven published result files pass JSON Schema/SARIF validation. Historical files have not been hand-edited. No request-level traces or complete historical run directories are committed. |
| `src/` | Frontend consumes published results, validates references and recomputes scores. All 52 tests, lint and production build pass. Its Paper tab explores the source article; the new manuscript is a separate deliverable. |
| `.github/workflows/ci.yml` | Unit, frontend, testbed and deployment workflows exist. This audit did not execute remote CI or deploy anything. CI smoke measurements must not substitute for full experimental measurements. |
| `docs/` | Source extraction, architecture, check catalogue, experiment protocol, replication protocol and viva notes are present. New manuscript, evidence and audit complete the reporting package. |

## Changes completed in this audit

1. E2 isolation success now requires the complete unique catalogue, explicit blocked outcomes on every hardened path and passing positive controls. An error, missing row or duplicate cannot pass merely because the open-path count is zero.
2. E3 success now requires complete unique trigger evidence, correct attribution, timely detection, expected silence and no recorded false positives. The publisher and live gate share the same predicates.
3. Thirteen regression cases were added for valid evidence and corrupted outcomes, including a live-gate attribution regression.
4. `scripts/research_evidence.py` independently recomputes check scores and latency statistics, verifies run validity, checks detection outcomes and hashes input files. It adds descriptive ranges and explicitly qualified illustrative uncertainty calculations.
5. The manuscript reports accurate denominators: 29 applicable checks out of 30; 27 hardened passes, two waived failures and one skip. Both configurations met the 25 ms SLO. The optional SMT hypothesis is inconclusive. Literature replication results are excluded.
6. README links were corrected and submission materials added to the allowed documentation paths in `.gitignore`.

## Verification evidence

- Python: **173 passed, 1 skipped** after the fixes. The skip is the test requiring published literature-replication results.
- Auditor and experiment Ruff checks: passed.
- Frontend: **52 passed**, lint passed, TypeScript and Vite production build passed.
- Published audits, SARIF and E1-E3: all **7 files validated**.
- Replication corpus snapshots, NVD snapshot and frozen classifier: hash integrity passed; annotation **0/110**.
- Independent reanalysis: insecure and hardened weighted coverage 19.51% and 93.90%; noisy p99 reduction 65.88%; complete E2 and E3 evidence passes the stricter predicates.
- PDF: rendered page images inspected before delivery. The editable manuscript and renderer are included.

## Remaining work before submission

1. **Check any venue-specific submission requirements.** The manuscript now uses the official IEEEtran conference class and includes Atharva Agrawal and Niti Priya with their supplied emails and IIIT Dharwad affiliation. No conference acceptance, publication identifier, funding, or supervisor has been invented.
2. **Confirm the scope interpretation with the instructor if needed.** The selected paper is a survey, not an algorithm paper. This work implements its future-work design requirements. If the assignment specifically demands reproduction of an algorithm, the present work needs instructor acceptance or a different primary implementation paper; changing the wording cannot solve that mismatch.
3. **Review the waivers as project owner.** `testbed/waivers.yaml` still records `approvedBy: project owner (pending review)`. Check the actual host exposure and compensating controls; only the owner should record approval. Current configured expiries are 31 December 2026. A passing gate must not be described as documented owner acceptance.
4. **Rerun full experiments on the final submission revision.** Start Docker Desktop, run `python scripts/lab.py doctor`, `python scripts/lab.py run-all --variant full`, then `python scripts/lab.py publish`. Retain raw run directories, load-test output and monitoring traces. The existing measured revision is `dffa2c70c553`; this checkout started at `d744dd2` and now includes uncommitted audit fixes. Do not claim the audit reran the live experiments.
5. **If claiming the optional literature replication, finish the blind human annotation.** Run `python scripts/lab.py rep annotate`, label all 110 screens without looking at hidden predictions, then `rep validate`, `rep analyze` and `rep publish`. Human labels must not be generated by this assistant and represented as blind human judgments. The core manuscript is validly scoped without this extension.

Optional research extensions, not prerequisites for the scoped manuscript: execute the optional SMT arm on suitable hardware; add DET-09 validation; measure monitoring overhead; add control ablations; repeat on multiple hosts and more workloads; extend false-positive observation; benchmark other tools. These would improve evidence strength and publication prospects but have not been presented as completed work.

## Reanalysis and manuscript reproduction

Use Python 3.12 with dependencies in `auditor/requirements.lock` and `auditor/requirements-dev.lock`. Put `auditor/src` and `experiments` on `PYTHONPATH`, run `python scripts/research_evidence.py`, and inspect `docs/research/evidence.json`. For the PDF, use the bundled artifact Python runtime with ReportLab and run `python scripts/build_research_paper.py --compiler PATH_TO_TECTONIC_OR_PDFLATEX`. The builder creates vector figures and compiles `docs/research/IsoLab_IEEE.tex` with the official IEEEtran conference class. The LaTeX source and figure PDFs can also be uploaded to Overleaf. Consult `README.md` for the normal Docker-based project workflow.
# November 11, 2026 research refinement

Current implementation and presentation: [research/DEMO.md](research/DEMO.md).
The project now adds a selected ACM M2 startup integrity control, six-theme defense crosswalk,
E4 configuration fault injection (10/10 detected), E5 subprocess challenges (5/5 passed),
and six clean/altered-file checks in the built tenant images (6/6 passed).
Four mapped hardened themes satisfy the strict all-target verification rule; two retain provider
exceptions and receive no full credit. The 2024 neural classifier remains future work.
The revised IEEE paper separates these new experiments from the October E1–E3 benchmark.
The audit below records the earlier review and should be read with this update.

