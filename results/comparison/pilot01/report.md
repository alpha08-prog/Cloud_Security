# Single-host matched pilot

This is a measured architecture adaptation on shared local telemetry, not a reproduction of the 2024 paper.

| Workload | Method | Test runs | TP / TN / FP / FN | F1 | FPR | AUC | Train seconds |
|---|---|---:|---|---:|---:|---:|---:|
| payments | adapted-2024-ae-lstm | 24 | 8 / 15 / 0 / 1 | 0.941 | 0.000 | 1.000 | 43.16 |
| payments | isolab-resource-logistic | 24 | 9 / 15 / 0 / 0 | 1.000 | 0.000 | 1.000 | 0.01 |
| payments | cpu-threshold | 24 | 7 / 15 / 0 / 2 | 0.875 | 0.000 | 1.000 | 0.00 |
| payments | isolab-det08 | 24 | 3 / 15 / 0 / 6 | 0.500 | 0.000 | undefined | 0.00 |
| rf | adapted-2024-ae-lstm | 12 | 3 / 9 / 0 / 0 | 1.000 | 0.000 | 1.000 | 56.55 |
| rf | isolab-resource-logistic | 12 | 3 / 9 / 0 / 0 | 1.000 | 0.000 | 1.000 | 0.01 |
| rf | cpu-threshold | 12 | 3 / 9 / 0 / 0 | 1.000 | 0.000 | 1.000 | 0.00 |
| rf | isolab-det08 | 12 | 3 / 9 / 0 / 0 | 1.000 | 0.000 | undefined | 0.00 |
| svm | adapted-2024-ae-lstm | 12 | 3 / 8 / 0 / 1 | 0.857 | 0.000 | 0.969 | 85.78 |
| svm | isolab-resource-logistic | 12 | 1 / 8 / 0 / 3 | 0.400 | 0.000 | 0.938 | 0.00 |
| svm | cpu-threshold | 12 | 2 / 8 / 0 / 2 | 0.667 | 0.000 | 0.938 | 0.00 |
| svm | isolab-det08 | 12 | 3 / 8 / 0 / 1 | 0.857 | 0.000 | undefined | 0.00 |

## Performance controls

Intervals bootstrap independent run summaries; job duration and request p99 are different metrics.

| Workload | Profile | Scenario | Runs | Median ms | 95% interval | Background batches/s |
|---|---|---|---:|---:|---|---:|
| payments | hardened | benign | 10 | 4.248 | 4.070–4.494 | 34.129 |
| payments | hardened | bursty | 10 | 4.129 | 4.033–4.355 | 16.755 |
| payments | hardened | clean | 10 | 3.842 | 3.682–4.047 | 0.000 |
| payments | hardened | sustained | 10 | 4.287 | 4.115–4.541 | 34.124 |
| payments | shared | benign | 10 | 6.221 | 5.754–6.849 | 90.310 |
| payments | shared | bursty | 10 | 8.755 | 8.529–9.666 | 50.126 |
| payments | shared | clean | 10 | 3.601 | 3.580–3.758 | 0.000 |
| payments | shared | sustained | 10 | 10.997 | 10.472–15.567 | 98.953 |
| rf | hardened | clean | 10 | 635.270 | 627.546–658.729 | 0.000 |
| rf | hardened | sustained | 10 | 716.498 | 706.876–754.865 | 31.131 |
| rf | shared | clean | 10 | 648.497 | 634.820–656.797 | 0.000 |
| rf | shared | sustained | 10 | 1103.983 | 1069.521–1154.964 | 89.499 |
| svm | hardened | clean | 10 | 486.640 | 463.992–513.840 | 0.000 |
| svm | hardened | sustained | 10 | 539.942 | 525.398–568.816 | 31.506 |
| svm | shared | clean | 10 | 475.962 | 467.077–496.267 | 0.000 |
| svm | shared | sustained | 10 | 901.566 | 868.672–1008.845 | 88.731 |

## Interpretation limits

- F1 and FPR are held-out run-level metrics, not event-window metrics or attack detection rates.
- Thresholds and preprocessing were selected using training/validation only.
- Neural and logistic scores use the final 30 seconds; this is offline run classification, not an online detection-delay comparison.
- The hardened arm is a CPU-control/least-privilege adaptation; it does not remeasure the historical security checks.
- Collector CPU/RSS samples do not replace a monitoring-disabled overhead experiment.
- Ten runs per cell leave three held-out runs per cell; uncertainty and single-host limits preclude general superiority claims.
- Published 2024 metrics are contextual only and must not be subtracted from these local results to claim improvement.
