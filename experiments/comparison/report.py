"""Report only observed results, including unfavorable and undefined metrics."""
import json
from pathlib import Path
import statistics
import sys
from isolab.comparison import median_interval


def main():
    root=Path(sys.argv[1])
    summary=json.loads((root/'evaluation/summary.json').read_text())
    runs=[json.loads(p.read_text()) for p in root.glob('*/result.json')]
    lines=['# Single-host matched pilot', '',
           'This is a measured architecture adaptation on shared local telemetry, not a reproduction of the 2024 paper.', '',
           '| Workload | Method | Test runs | TP / TN / FP / FN | F1 | FPR | AUC | Train seconds |',
           '|---|---|---:|---|---:|---:|---:|---:|']
    def fmt(value):
        return 'undefined' if value is None else f'{value:.3f}'
    for result in summary['results']:
        m=result['metrics']
        counts=' / '.join(str(m[k]) for k in ('tp','tn','fp','fn'))
        lines.append(f"| {result['workload']} | {result['method']} | {result['testRuns']} | {counts} | {fmt(m['f1'])} | {fmt(m['falsePositiveRate'])} | {fmt(m['auc'])} | {result['trainingSeconds']:.2f} |")
    lines += ['', '## Performance controls', '',
              'Intervals bootstrap independent run summaries; job duration and request p99 are different metrics.', '',
              '| Workload | Profile | Scenario | Runs | Median ms | 95% interval | Background batches/s |',
              '|---|---|---|---:|---:|---|---:|']
    for key in sorted({(r['workload'],r['profile'],r['scenario']) for r in runs}):
        group=[r for r in runs if (r['workload'],r['profile'],r['scenario'])==key]
        ci=median_interval([r['performanceMs'] for r in group])
        bg=statistics.median(r['backgroundBatchesPerSecond'] for r in group)
        lines.append('| '+' | '.join(key)+f" | {len(group)} | {ci['median']:.3f} | {ci['low']:.3f}–{ci['high']:.3f} | {bg:.3f} |")
    lines += ['', '## Interpretation limits', '',
              '- F1 and FPR are held-out run-level metrics, not event-window metrics or attack detection rates.',
              '- Thresholds and preprocessing were selected using training/validation only.',
              '- Neural and logistic scores use the final 30 seconds; this is offline run classification, not an online detection-delay comparison.',
              '- The hardened arm is a CPU-control/least-privilege adaptation; it does not remeasure the historical security checks.',
              '- Collector CPU/RSS samples do not replace a monitoring-disabled overhead experiment.',
              '- Ten runs per cell leave three held-out runs per cell; uncertainty and single-host limits preclude general superiority claims.',
              '- Published 2024 metrics are contextual only and must not be subtracted from these local results to claim improvement.', '']
    (root/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(root/'report.md')


if __name__=='__main__':
    main()
