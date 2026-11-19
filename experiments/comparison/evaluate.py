"""Fit on training runs, select thresholds on validation, evaluate once on test.

2024-inspired architecture adaptation, NOT a reproduction of published numbers.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from isolab.comparison import confusion, split_runs, validate_predictions
from isolab.comparison_models import service_models
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import MinMaxScaler, StandardScaler


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def choose_threshold(labels, scores):
    candidates = sorted(set([0., 1., *map(float,scores)]))
    def rank(threshold):
        m = confusion(labels, [int(s >= threshold) for s in scores])
        return (m['f1'] or 0, -(m['falsePositiveRate'] or 0), threshold)
    return max(candidates,key=rank)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('input',type=Path)
    p.add_argument('--epochs',type=int,default=1000)
    p.add_argument('--window',type=int,default=6)
    args = p.parse_args()
    target = args.input/'evaluation'
    if (target/'summary.json').exists():
        raise RuntimeError('Completed evaluation already exists; do not tune against its held-out results')
    target.mkdir(exist_ok=True)
    runs = []
    for path in sorted(args.input.glob('*/result.json')):
        row = json.loads(path.read_text())
        row['telemetry'] = [json.loads(line) for line in (path.parent/'telemetry.jsonl').read_text().splitlines()]
        if row['status'] != 'measured' or len(row['telemetry']) < args.window:
            raise RuntimeError('Incomplete run: '+row['runId'])
        runs.append(row)
    manifest=json.loads((args.input/'manifest.json').read_text())
    expected={f"{r['workload']}-{r['profile']}-{r['scenario']}-{r['rep']:02}" for r in manifest['schedule']}
    if {r['runId'] for r in runs} != expected:
        raise RuntimeError('Run matrix incomplete or contains unexpected runs; no selective evaluation')
    dump(target/'raw-hashes.json', {str(p.relative_to(args.input)):hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(args.input.glob('*/*.json*'))})
    cells = sorted({(r['workload'],r['profile'],r['scenario']) for r in runs})
    splits = {}
    for cell in cells:
        subset = [r['runId'] for r in runs if (r['workload'],r['profile'],r['scenario']) == cell]
        splits.update(split_runs(subset))
    dump(target/'splits.json',splits)
    import tensorflow as tf
    tf.keras.utils.set_random_seed(20261117)
    summaries, predictions = [], []
    for workload in sorted({r['workload'] for r in runs}):
        subset = [r for r in runs if r['workload']==workload]
        thresholds = {}
        for profile in sorted({r['profile'] for r in subset}):
            clean = [r['performanceMs'] for r in subset
                     if r['profile']==profile and r['scenario']=='clean' and splits[r['runId']]=='train']
            if not clean:
                raise RuntimeError('Missing independent clean training baseline')
            thresholds[profile] = max(clean)*1.2
        y = np.array([int(r['performanceMs']>thresholds[r['profile']] or r['failures']>0) for r in subset])
        x = np.array([[t['features'] for t in r['telemetry'][-args.window:]] for r in subset],dtype=np.float32)
        if not np.isfinite(x).all():
            raise RuntimeError('Nonfinite telemetry')
        indices = {s:np.array([i for i,r in enumerate(subset) if splits[r['runId']]==s])
                   for s in ('train','validation','test')}
        tr,va,te = (indices[s] for s in ('train','validation','test'))
        if any(len(set(y[idx]))<2 for idx in (tr,va,te)):
            raise RuntimeError(
                f'{workload}: both classes required in each split; preserve data and report insufficiency'
            )
        start = time.perf_counter()
        # Sigmoid autoencoder requires bounded input. Train-only min/max scaling is
        # an explicit adaptation of the source's ambiguous robust-scaling wording.
        scale = MinMaxScaler(clip=True).fit(x[tr].reshape(-1,x.shape[-1]))
        xs = scale.transform(x.reshape(-1,x.shape[-1])).reshape(x.shape)
        ae,encoder,model = service_models(x.shape[-1],args.window)
        # Explicit batch loop avoids private tf.data threadpool creation on small hosts.
        def fit(model, a,b,av,bv,patience):
            best, wait, weights = float('inf'),0,None
            history=[]
            for _epoch in range(args.epochs):
                model.reset_metrics()
                for offset in range(0,len(a),512):
                    model.train_on_batch(a[offset:offset+512],b[offset:offset+512])
                prediction = model(av,training=False).numpy()
                loss = float(np.sqrt(np.mean((prediction-bv)**2))) if prediction.shape==bv.shape else float(
                    -np.log(np.clip(prediction[np.arange(len(bv)),bv],1e-8,1)).mean())
                history.append(loss)
                if loss < best-1e-6:
                    best,wait,weights=loss,0,model.get_weights()
                else:
                    wait+=1
                if wait>=patience:
                    break
            model.set_weights(weights)
            return history
        ae_history=fit(ae,xs[tr].reshape(-1,x.shape[-1]),xs[tr].reshape(-1,x.shape[-1]),
                       xs[va].reshape(-1,x.shape[-1]),xs[va].reshape(-1,x.shape[-1]),10)
        z=encoder(xs.reshape(-1,x.shape[-1]),training=False).numpy().reshape(len(x),args.window,20)
        model_history=fit(model,z[tr],y[tr],z[va],y[va],20)
        neural_train=time.perf_counter()-start
        start=time.perf_counter()
        neural=model(z,training=False).numpy()[:,1]
        neural_infer=(time.perf_counter()-start)/len(x)
        model.save(target/(workload+'-lstm.keras'))
        encoder.save(target/(workload+'-encoder.keras'))
        start=time.perf_counter()
        aggregate=x.mean(axis=1)
        lightweight_scale=StandardScaler().fit(aggregate[tr])
        a=lightweight_scale.transform(aggregate)
        lightweight=LogisticRegression(
            C=1, class_weight='balanced',random_state=20261117,max_iter=2000,
        ).fit(a[tr],y[tr])
        lightweight_train=time.perf_counter()-start
        start=time.perf_counter()
        light=lightweight.predict_proba(a)[:,1]
        lightweight_infer=(time.perf_counter()-start)/len(x)
        methods={'adapted-2024-ae-lstm':neural,'isolab-resource-logistic':light,
                 'cpu-threshold':np.clip(aggregate[:,16]/12,0,1),
                 'isolab-det08':np.array([int(any(t['det08'] for t in r['telemetry'])) for r in subset])}
        for method,scores in methods.items():
            threshold=.5 if method=='isolab-det08' else choose_threshold(y[va].tolist(),scores[va])
            metrics=confusion(y[te].tolist(),(scores[te]>=threshold).astype(int).tolist())
            metrics['auc']=float(roc_auc_score(y[te],scores[te])) if method!='isolab-det08' else None
            summaries.append(dict(workload=workload,method=method,threshold=float(threshold),metrics=metrics,
                                  testRuns=len(te),groundTruthThresholdMs=thresholds,
                                  trainingSeconds=(neural_train if method=='adapted-2024-ae-lstm'
                                                   else lightweight_train if method=='isolab-resource-logistic' else 0),
                                  inferenceSecondsPerRun=(neural_infer if method=='adapted-2024-ae-lstm'
                                                          else lightweight_infer
                                                          if method=='isolab-resource-logistic' else None)))
            for i,r in enumerate(subset):
                predictions.append(dict(method=method,runId=r['runId'],timestamp=r['ended'],split=splits[r['runId']],
                                        label=int(y[i]),score=float(scores[i]),threshold=float(threshold)))
        dump(target/(workload+'-training.json'),{'autoencoderValidationLoss':ae_history,'classifierValidationLoss':model_history,
              'minMaxMinimum':scale.data_min_.tolist(),'minMaxMaximum':scale.data_max_.tolist(),
              'logisticCoefficient':lightweight.coef_.tolist(),'logisticIntercept':lightweight.intercept_.tolist(),
              'standardMean':lightweight_scale.mean_.tolist(),'standardScale':lightweight_scale.scale_.tolist()})
        tf.keras.backend.clear_session()
    validate_predictions(predictions)
    dump(target/'predictions.json',predictions)
    dump(target/'summary.json',{'basis':'Measured single-host adaptation; not original-paper reproduction',
                               'manifestSha256':hashlib.sha256((args.input/'manifest.json').read_bytes()).hexdigest(),
                               'results':summaries})
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    main()
