"""Bounded pilot: collect, train, report; machine-readable progress and failures."""
import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host-workspace',required=True)
    parser.add_argument('--output',default='/workspace/results/comparison/pilot01')
    args=parser.parse_args()
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    started=time.time()
    def status(state, **extra):
        data=dict(state=state,startedAt=datetime.fromtimestamp(started,UTC).isoformat(),
                  updatedAt=datetime.now(UTC).isoformat(),elapsedSeconds=time.time()-started,**extra)
        tmp=out/'status.tmp'
        tmp.write_text(json.dumps(data,indent=2)+'\n')
        tmp.replace(out/'status.json')
        print(json.dumps(data),flush=True)
    try:
        status('collecting',plannedRuns=160,collectionBudgetHours=5.5,totalBudgetHours=8)
        with (out/'collection.log').open('w') as log:
            subprocess.run([sys.executable,'experiments/comparison/collect.py','--host-workspace',args.host_workspace,
                            '--output',str(out),'--campaign','isolab-pilot','--pilot','--max-hours','5.5'],
                           stdout=log,stderr=subprocess.STDOUT,check=True)
        status('training',completedRuns=len(list(out.glob('*/result.json'))))
        remaining=max(1,8*3600-(time.time()-started)-120)
        with (out/'training.log').open('w') as log:
            subprocess.run([sys.executable,'experiments/comparison/evaluate.py',str(out)],
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=remaining)
        status('reporting')
        subprocess.run([sys.executable,'experiments/comparison/report.py',str(out)],check=True)
        status('complete',report=str(out/'report.md'))
    except Exception as exc:
        status('incomplete',error=f'{type(exc).__name__}: {exc}',
               completedRuns=len(list(out.glob('*/result.json'))))
        raise


if __name__=='__main__':
    main()
