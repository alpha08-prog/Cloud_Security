# Bounded matched-comparison pilot

This is a single-host architecture adaptation, not a reproduction of the paper's
411-feature distributed detector. Read `docs/research/comparison-protocol.md` for
the fixed conditions, feature/scaling deviations and claim limits.

The pilot evaluates 160 independent runs and then trains/evaluates four methods:
the 2024-inspired AE/LSTM, actual IsoLab DET-08, CPU threshold, and a proposed
lightweight resource-based logistic model. No model is guaranteed to win.

The controller requires the Docker socket, host PID namespace, SYS_PTRACE for
process statistics, and a read-only host cgroup mount. Use only the isolated lab.
It creates and cleans up `isolab-pilot-victim` and `isolab-pilot-noise`, leaving
other projects untouched. Measurements and model outputs go under
`results/comparison/pilot01`; historical published results are not overwritten.

```powershell
docker build -t isolab/comparison:20261117 -f experiments/comparison/Dockerfile .
docker run -d --name isolab-pilot-controller --pid host --cgroupns host --cap-add SYS_PTRACE --network host --cpuset-cpus 0-3 --memory 3g -v C:/Users/agraw/Cloud_Security:/workspace -v /var/run/docker.sock:/var/run/docker.sock -v /sys/fs/cgroup:/host/cgroup:ro isolab/comparison:20261117 python experiments/comparison/pilot.py --host-workspace /run/desktop/mnt/host/c/Users/agraw/Cloud_Security
docker logs --tail 20 isolab-pilot-controller
Get-Content results/comparison/pilot01/status.json
```

Expected outputs: manifest/schedule, per-run requests or completed jobs, telemetry,
background throughput, detector events, training logs, splits, prediction records,
saved models, evaluation summary, and `report.md`. `status.json` records `complete`
only after the report exists. An `incomplete` state includes the error; inspect
collection/training logs. Keep the computer awake and Docker running for the pilot.
Do not change comparison scripts while the experiment is in progress.

The collector checks its deadline between runs; Spark readiness is capped at three
minutes. A failed run remains on disk and is not silently reused. A rerun should
use a new output directory. Stopping Docker interrupts the campaign; a partial
matrix cannot be advertised as the planned comparison.
