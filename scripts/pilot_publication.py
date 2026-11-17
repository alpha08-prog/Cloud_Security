"""Audit completed pilot evidence before generating publication tables/figures.

Does not alter the main manuscript or running experiment. Confidence intervals
are a post-hoc paired run-bootstrap sensitivity analysis, not preregistered tests.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'experiments'))
from isolab.comparison import confusion, validate_predictions


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def percentile(values, fraction):
    ordered=sorted(values)
    index=(len(ordered)-1)*fraction
    left=math.floor(index)
    return ordered[left]+(ordered[min(left+1,len(ordered)-1)]-ordered[left])*(index-left)


def paired_f1_interval(a,b,draws=5000):
    if [(r['runId'],r['label']) for r in a] != [(r['runId'],r['label']) for r in b]:
        raise ValueError('Unpaired method comparison')
    rng=random.Random(20261117)
    values=[]
    for _ in range(draws):
        indices=rng.choices(range(len(a)),k=len(a))
        scores=[]
        for rows in (a,b):
            m=confusion([rows[i]['label'] for i in indices],
                        [int(rows[i]['score']>=rows[i]['threshold']) for i in indices])
            scores.append(m['f1'])
        if all(s is not None for s in scores):
            values.append(scores[0]-scores[1])
    if not values:
        return None
    return dict(low=percentile(values,.025),high=percentile(values,.975),validDraws=len(values),
                interpretation='post-hoc paired run bootstrap; no multiple-comparison correction')


def audit(root):
    if read(root/'status.json')['state']!='complete':
        raise RuntimeError('Pilot has not completed; do not publish interim comparisons')
    summary=read(root/'evaluation/summary.json')
    digest=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()
    if digest!=summary['manifestSha256']:
        raise RuntimeError('Manifest changed since evaluation')
    for name,digest in read(root/'evaluation/raw-hashes.json').items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Raw evidence changed: '+name)
    predictions=read(root/'evaluation/predictions.json')
    validate_predictions(predictions)
    runs={r['runId']:r for r in (read(p) for p in root.glob('*/result.json'))}
    schedule=read(root/'manifest.json')['schedule']
    expected={f"{r['workload']}-{r['profile']}-{r['scenario']}-{r['rep']:02}" for r in schedule}
    if set(runs)!=expected or len(runs)!=160:
        raise RuntimeError('Pilot matrix differs from fixed 160-run schedule')
    split=read(root/'evaluation/splits.json')
    if set(split)!=set(runs):
        raise RuntimeError('Split coverage mismatch')
    for item in summary['results']:
        rows=[r for r in predictions if r['method']==item['method'] and
              runs[r['runId']]['workload']==item['workload'] and r['split']=='test']
        measured=confusion([r['label'] for r in rows],[int(r['score']>=r['threshold']) for r in rows])
        for key,value in measured.items():
            if value!=item['metrics'][key]:
                raise RuntimeError('Metric mismatch: '+key)
        if len(rows)!=item['testRuns']:
            raise RuntimeError('Test count mismatch')
        for row in rows:
            source=runs[row['runId']]
            label=int(source['performanceMs']>item['groundTruthThresholdMs'][source['profile']] or source['failures']>0)
            if row['label']!=label or split[row['runId']]!='test':
                raise RuntimeError('Label or partition mismatch')
    for run in runs.values():
        path=root/run['runId']
        if run['workload']=='payments':
            rows=[r for r in jsonl(path/'requests.jsonl') if r['scheduled']>=run['started']+10]
            value=percentile([r['latencyMs'] for r in rows],.99)
            if not math.isclose(value,run['performanceMs'],rel_tol=1e-9):
                raise RuntimeError('Request p99 does not reproduce')
        else:
            rows=[r for r in jsonl(path/'victim/jobs.jsonl') if r['started']>=run['started'] and r['ended']<=run['ended']]
            # A job can finish while the observer is taking its terminal snapshot.
            # Report discrepancies for manual inspection rather than silently correcting.
            value=statistics.median(r['durationMs'] for r in rows)
            if not math.isclose(value,run['performanceMs'],rel_tol=.01):
                raise RuntimeError('Job-time summary needs terminal-snapshot review: '+run['runId'])
    comparisons=[]
    for workload in sorted({r['workload'] for r in runs.values()}):
        def rows(method):
            return sorted([r for r in predictions if r['method']==method and r['split']=='test' and
                           runs[r['runId']]['workload']==workload],key=lambda r:r['runId'])
        comparisons.append(dict(workload=workload,
                                logisticMinusNeuralF1Interval=paired_f1_interval(rows('isolab-resource-logistic'),rows('adapted-2024-ae-lstm'))))
    return summary,runs,comparisons


def artifacts(summary,runs,comparisons,dest):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'pdf.fonttype':42,'font.size':9})
    methods=['adapted-2024-ae-lstm','isolab-resource-logistic','cpu-threshold','isolab-det08']
    labels=['Adapted AE/LSTM','Resource logistic','CPU threshold','DET-08']
    workloads=['payments','rf','svm']
    fig,axes=plt.subplots(1,2,figsize=(7,2.7))
    for j,(method,label) in enumerate(zip(methods,labels)):
        rows=[next(r for r in summary['results'] if r['workload']==w and r['method']==method) for w in workloads]
        for ax,key in zip(axes,['f1','falsePositiveRate']):
            ax.plot(range(3),[r['metrics'][key] for r in rows],marker=['o','s','^','x'][j],label=label)
            ax.set_xticks(range(3),['Payments','Spark RF','Spark SVM'])
            ax.set_ylim(-.03,1.03)
            ax.grid(alpha=.2)
    axes[0].set_ylabel('Held-out run F1')
    axes[1].set_ylabel('Held-out run false-positive rate')
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc='lower center',ncol=4,fontsize=8)
    fig.tight_layout(rect=(0,.14,1,1))
    fig.savefig(dest/'ieee-pilot-detection.pdf')
    fig.savefig(ROOT/'tmp/research/pilot-detection.png',dpi=160)
    plt.close(fig)
    table=[r'\begin{table*}[t]',r'\caption{Held-out single-host pilot: run-level detection and fitting cost}',
           r'\label{tab:pilot}',r'\centering\small',r'\begin{tabular}{llrrrrrr}',r'\toprule',
           r'Workload & Method & Test runs & Precision & Recall & F1 & FPR & Fit time (s) \\',r'\midrule']
    for w in workloads:
        for method,label in zip(methods,labels):
            r=next(r for r in summary['results'] if r['workload']==w and r['method']==method)
            def fmt(v):
                return '--' if v is None else f'{v:.3f}'
            fields=[w.upper() if w!='payments' else 'Payments',label,str(r['testRuns']),
                    *[fmt(r['metrics'][k]) for k in ('precision','recall','f1','falsePositiveRate')],
                    f"{r['trainingSeconds']:.5f}" if method=='isolab-resource-logistic' else
                    f"{r['trainingSeconds']:.2f}" if method=='adapted-2024-ae-lstm' else '--']
            table.append(' & '.join(fields)+r' \\')
    table += [r'\bottomrule',r'\end{tabular}',r'\end{table*}']
    (dest/'pilot-results.tex').write_text('\n'.join(table)+'\n')
    groups=defaultdict(list)
    for r in runs.values():
        groups[r['workload'],r['profile'],r['scenario']].append(r)
    effects=[]
    for w in workloads:
        shared=statistics.median(r['performanceMs'] for r in groups[w,'shared','sustained'])
        hardened=statistics.median(r['performanceMs'] for r in groups[w,'hardened','sustained'])
        background_shared=statistics.median(r['backgroundBatchesPerSecond'] for r in groups[w,'shared','sustained'])
        background_hardened=statistics.median(r['backgroundBatchesPerSecond'] for r in groups[w,'hardened','sustained'])
        effects.append(dict(workload=w,sharedMs=shared,hardenedMs=hardened,reductionPct=100*(1-hardened/shared),
                            backgroundShared=background_shared,backgroundHardened=background_hardened,
                            backgroundReductionPct=100*(1-background_hardened/background_shared)))
    control=[r'\begin{table*}[t]',r'\caption{Sustained-contention pilot: performance benefit and competing-workload cost}',
             r'\label{tab:pilotcontrols}',r'\centering\small',r'\begin{tabular}{lrrrrrr}',r'\toprule',
             r'Workload & Shared (ms) & Hardened (ms) & Reduction (\%) & Shared bg. & Hardened bg. & Bg. loss (\%) \\',r'\midrule']
    for effect in effects:
        control.append(' & '.join([effect['workload'].upper(),*[f'{effect[k]:.3f}' for k in
                       ('sharedMs','hardenedMs','reductionPct','backgroundShared','backgroundHardened','backgroundReductionPct')]])+r' \\')
    control += [r'\bottomrule',r'\end{tabular}',r'\smallskip',
                r'\parbox{.95\textwidth}{\footnotesize Ten independent runs per cell; entries are medians of run summaries. Payments uses request p99; RF and SVM use median completed-job duration. Background (bg.) throughput is completed 100,000-hash batches per second, not tenant requests.}',r'\end{table*}']
    (dest/'pilot-controls.tex').write_text('\n'.join(control)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(7,2.7))
    for j,profile in enumerate(['shared','hardened']):
        for i,w in enumerate(workloads):
            clean=statistics.median(r['performanceMs'] for r in groups[w,profile,'clean'])
            noisy=[r['performanceMs']/clean for r in groups[w,profile,'sustained']]
            base_bg=statistics.median(r['backgroundBatchesPerSecond'] for r in groups[w,'shared','sustained'])
            bg=[r['backgroundBatchesPerSecond']/base_bg for r in groups[w,profile,'sustained']]
            x=i+(-.16 if j==0 else .16)
            for ax,values in zip(axes,[noisy,bg]):
                ax.scatter([x+(k-4.5)*.012 for k in range(len(values))],values,s=12,
                           color=['#777777','#254e70'][j],label=profile.capitalize() if i==0 else None)
                ax.plot([x-.10,x+.10],[statistics.median(values)]*2,color='black',linewidth=1)
    for ax in axes:
        ax.set_xticks(range(3),['Payments','Spark RF','Spark SVM'])
        ax.axhline(1,linestyle='--',color='black',linewidth=.6)
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Victim time / clean profile median')
    axes[1].set_ylabel('Background throughput / shared median')
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(dest/'ieee-pilot-controls.pdf')
    fig.savefig(ROOT/'tmp/research/pilot-controls.png',dpi=160)
    plt.close(fig)
    result=dict(basis=summary['basis'],manifestSha256=summary['manifestSha256'],results=summary['results'],
                postHocUncertainty=comparisons,controlEffects=effects)
    (dest/'pilot-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT/'results/comparison/pilot01')
    parser.add_argument('--write-artifacts',action='store_true')
    args=parser.parse_args()
    summary,runs,comparisons=audit(args.root)
    print(f'Validated {len(runs)} runs and {len(summary["results"])} method/workload summaries')
    if args.write_artifacts:
        artifacts(summary,runs,comparisons,ROOT/'docs/research')
