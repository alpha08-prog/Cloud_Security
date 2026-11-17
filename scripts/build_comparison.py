"""Generate original historical-data figures and numerical context, not new runs."""
import hashlib
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'pdf.fonttype': 42, 'font.size': 9})

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs/research'


def main():
    path = ROOT / 'results/published/e1.json'
    data = json.loads(path.read_text())
    if not data['runs'] or any(not r['valid'] for r in data['runs']):
        raise ValueError('Historical figure requires valid run summaries')
    (ROOT / 'tmp/research').mkdir(parents=True, exist_ok=True)
    rows = []
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.7))
    for index, profile in enumerate(('insecure', 'hardened')):
        runs = [r for r in data['runs'] if r['profile'] == profile]
        baseline = statistics.median(r['latencyMs']['p99'] for r in runs if r['arm'] == 'baseline')
        noisy = statistics.median(r['latencyMs']['p99'] for r in runs if r['arm'] == 'noisy')
        rows.append(dict(profile=profile, baselineP99Ms=baseline, noisyP99Ms=noisy,
                         interferenceFactor=noisy / baseline, inflationPct=100 * (noisy / baseline - 1),
                         sloHeadroomMs=25 - noisy))
        for arm_index, arm in enumerate(('baseline', 'noisy')):
            subset = [r for r in runs if r['arm'] == arm]
            x = index * 2 + arm_index
            for j, run in enumerate(subset):
                axes[0].scatter(x + (j - 1) * .08, run['latencyMs']['p99'], color=['#777777', '#254e70'][index], s=22)
                axes[1].scatter(run['victimCpuPressurePct'], run['latencyMs']['p99'],
                                color=['#777777', '#254e70'][index], marker=['o', '^'][arm_index], s=25)
    axes[0].set_xticks(range(4), ['Weak\nclean', 'Weak\nnoise', 'Hard\nclean', 'Hard\nnoise'])
    axes[0].set_ylabel('Per-run request p99 (ms)')
    axes[1].set_xlabel('Victim CPU pressure (%)')
    axes[1].set_ylabel('Per-run request p99 (ms)')
    for ax in axes:
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(DEST / 'ieee-comparison-runs.pdf')
    fig.savefig(ROOT / 'tmp/research/comparison-runs.png', dpi=160)
    plt.close(fig)
    ledger = dict(schemaVersion='1.0', basis='Historical E1 reanalysis; not matched classifier results',
                  sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  measuredRunDates=sorted({r['startedAt'][:10] for r in data['runs']}),
                  published2024=dict(doi='10.1016/j.jnca.2024.103839', locator='Table 3, p. 11',
                                     RF=dict(TPR=.84, TNR=.89, AUC=.90, FMeasure=.90),
                                     SVM=dict(TPR=.87, TNR=.59, AUC=.82, FMeasure=.78)),
                  isolab=rows, matchedComparisonStatus='separate pilot; see pilot-evidence.json')
    (DEST / 'comparison-evidence.json').write_text(json.dumps(ledger, indent=2) + '\n')
    lines = [r'\begin{table}[t]', r'\caption{Historical performance isolation: derived metrics}',
             r'\label{tab:derived}', r'\centering\small', r'\begin{tabular}{lrrr}', r'\toprule',
             r'Profile & IF & Inflation (\%) & Headroom (ms) \\', r'\midrule']
    for row in rows:
        lines.append(f"{row['profile'].capitalize()} & {row['interferenceFactor']:.3f} & {row['inflationPct']:.1f} & {row['sloHeadroomMs']:.3f}" + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    (DEST / 'comparison-derived.tex').write_text('\n'.join(lines) + '\n')
    print(json.dumps(ledger, indent=2))


if __name__ == '__main__':
    main()
