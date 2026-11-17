# Matched comparison protocol, 2026-11-17

Status: implementation in progress; no matched measurements yet. Historical E1-E5
remain separate. This protocol supplements rather than rewrites docs/experiments.md.

## Experimental units and controls

Use one WSL2 Docker host. Record engine/kernel versions, available memory, CPU
topology, image digests, commit, dirty-tree diff hash, workload seeds and timestamps.
Do not equate its virtual CPU topology to four physical machines.

Workloads: payments at 50 requests/s; Spark RandomForest and linear SVM jobs with
fixed generated input. Calibrate Spark dataset size on clean runs before freezing
the campaign; preserve the dataset hash. Calibration data cannot enter evaluation.
Configurations: shared CPUs, quota-only, CPU-set-only, full hardened configuration.
Noise: none, sustained CPU, alternating 30-second CPU bursts, benign victim load.
Measure background completed work as well as victim performance.

Collect at five-second intervals, retaining engine and process-namespace features
and actual DET-08 events. Missing features are missing, not zero. No detector may
receive application latency as input. Ground truth comes from a frozen clean-run
latency/job-time threshold, not the noise schedule or detector output.

Use ten independent runs per workload/configuration/noise cell, seeded randomized
order and 30-second cooldown. Split executions 40/30/30 within cells; all windows
from one run stay together. Fit scaling and autoencoder on training only. Choose
classification thresholds on validation only. Report held-out metrics per workload.
Ten total runs leave only three held-out runs per cell: report wide uncertainty,
and do not treat correlated windows as independent replications.

## Baselines and adaptations

Compare actual IsoLab DET-08, CPU threshold and the 2024 service classifier.
The paper specifies 411 features (three containers, 137 each), encoder dense
512/256/128 ReLU, 20-unit sigmoid bottleneck, reversed decoder and sigmoid output;
LSTM 1024/512, dense 512/256 ReLU, two-class softmax; Adam learning rate 0.0001,
batch 512, up to 1000 epochs; autoencoder validation patience 10.

Feature availability, time-window length and scaling need a documented adaptation
ledger before training. The source's robust-scaling/range wording and sigmoid
decoder need explicit treatment; do not silently claim an exact replication.
Do not replace unavailable namespace metrics with CPU-only inputs and retain the
original method's name. The model factory is architecture scaffolding, not a
validated reproduction or a completed learning pipeline.

## Reporting and gates

Report precision, recall, F1, FPR, confusion counts, event delay, per-run p99/job
time, competing throughput, collector CPU/RSS, training time and inference cost.
Undefined metrics stay null. Bootstrap independent run summaries with fixed seed.
Retain all overload failures/dropped requests; exclude only documented harness
failures, and keep their records. Compare resource controls separately from detector
quality: monitoring alone is not a mitigation treatment.

Publish only with raw measurements, frozen protocol, run splits, source hashes and
prediction alignment checks. No publication claim of superiority is authorized by
successful software tests or the historical 65.9% internal latency reduction.

## Execution amendment (before new measurements)

The runnable collector uses 32 explicitly named engine/process aggregate features
from a victim and competing container, not the source's 411 features from three
service containers. Model name: `adapted-2024-ae-lstm`. This tests the architecture
on common local telemetry; it does not reproduce the original feature pipeline.
All learned methods receive the same feature arrays. DET-08 runs its existing
implementation; the CPU baseline receives only the competing CPU fraction.
The proposed `isolab-resource-logistic` uses fixed C=1 balanced logistic regression
on run-average resource features; no hyperparameter search on held-out results.

The execution harness uses an isolated Docker network and dedicated observer CPUs
0-3, victim CPUs 4-5, and competing CPUs 4-11 (shared) or 6-11 (separated).
Quota arms cap each tenant at two CPUs. The `hardened` comparison arm adds capability
drop and no-new-privileges to quota+CPU separation; it is a performance-control
adaptation, not the complete security profile from historical E1-E5.
The aggregate feature collection needs a host-PID observer with read-only cgroups.
Transient exited processes are skipped; denied access fails the measurement.

One run has twelve five-second samples (60 seconds); request evaluation discards
the initial ten seconds. Bursts alternate every 15 seconds. Benign competition
uses disjoint CPUs. Spark uses local[2], 20,000 seeded generated rows, eight features,
RF ten trees/depth five, SVM ten iterations; cached data initialization is excluded.
This is a small Spark adaptation, not HiBench/HDFS or the source's job sizes.
Smoke runs are never included in training or evaluation.

Run-level degradation label: performance above 1.2 times the maximum clean TRAINING
run value for that workload/profile, or any request error. This is fixed before
evaluation and independent of the injected noise label. Job time and request p99
remain separate response variables. The last six samples form each learned input.
The encoder uses training-only min/max scaling clipped to [0,1], aligning with its
sigmoid decoder. This differs from the source's scaling description. Classification
early stopping uses patience 20, AE patience 10, maximum 1000 epochs, batch 512;
the best validation weights are restored. Thresholds maximize validation F1,
breaking ties toward lower FPR and then higher threshold. Every split must have
both classes before reporting a learned comparison; otherwise report insufficiency.

The full matrix is 480 independent runs. Preserve raw data and partial progress;
no outcome-dependent early stopping or selection of favorable configurations.

## User-authorized bounded pilot

The user subsequently limited execution to a six-to-eight-hour pilot. The fixed
pilot comprises 160 runs: payments/shared+hardened/four scenarios/ten repetitions
(80), and RF+SVM/shared+hardened/clean+sustained/ten repetitions (80).
Quota-only and CPU-set-only ablations are excluded. Collection has a 5.5-hour
deadline checked between runs; training/reporting have the remaining eight-hour
budget. If the matrix is incomplete, evaluation fails closed rather than selecting
completed favorable cells. Smoke data are stored separately and excluded.
The time limit is operational, not an outcome-based stopping rule.
