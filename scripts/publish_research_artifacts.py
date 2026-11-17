"""Publish only the reviewed README/research artifacts using a fast-forward Git API commit.

Does not stage, reset, merge or commit the user's working checkout.
Run without --publish to inspect the exact file set.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REPO='repos/alpha08-prog/Cloud_Security'
FILES=['README.md','experiments/isolab/comparison.py','experiments/isolab/comparison_models.py',
       'experiments/tests/test_comparison.py','scripts/pilot_publication.py',
       'scripts/build_comparison.py','scripts/build_research_paper.py','scripts/check_research_paper.py',
       'scripts/research_evidence.py','scripts/package_pilot.py']
FILES += ['experiments/comparison/'+name for name in
          ['Dockerfile','README.md','workload.py','collect.py','evaluate.py','pilot.py','report.py','check.py']]
FILES += ['docs/research/'+name for name in ['IsoLab_Research_Paper.pdf','IsoLab_IEEE.tex',
          'IsoLab_Overleaf.zip','IsoLab_IEEE_Source.zip','IsoLab_Pilot_Evidence.zip','IEEE_README.txt',
          'pilot-section.tex','pilot-results.tex','pilot-controls.tex','pilot-evidence.json','pilot-report.md',
          'comparison-derived.tex','comparison-evidence.json','comparison-protocol.md','evidence.json',
          'ieee-architecture.pdf','ieee-latency.pdf','ieee-comparison-runs.pdf',
          'ieee-pilot-detection.pdf','ieee-pilot-controls.pdf']]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    for name in FILES:
        path=ROOT/name
        if not path.is_file() or path.stat().st_size>95_000_000:
            raise RuntimeError('Missing/oversized publication artifact: '+name)
    print(json.dumps({'files':FILES,'totalBytes':sum((ROOT/f).stat().st_size for f in FILES)},indent=2))
    if not args.publish:
        return
    scratch=ROOT/'tmp/github-publish'
    scratch.mkdir(parents=True,exist_ok=True)
    def api(endpoint, payload=None, method=None):
        command=['gh','api',REPO+'/'+endpoint]
        if payload is not None:
            path=scratch/'request.json'
            path.write_text(json.dumps(payload),encoding='utf-8')
            command += ['--method',method or 'POST','--input',str(path)]
        result=subprocess.run(command,capture_output=True,text=True,check=True,timeout=120)
        return json.loads(result.stdout)
    parent=api('git/ref/heads/main')['object']['sha']
    base=api('git/commits/'+parent)['tree']['sha']
    tree=[]
    hashes={}
    for name in FILES:
        content=(ROOT/name).read_bytes()
        hashes[name]=hashlib.sha256(content).hexdigest()
        blob=api('git/blobs',{'encoding':'base64','content':base64.b64encode(content).decode('ascii')})
        tree.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']})
        print('Prepared '+name,flush=True)
    created_tree=api('git/trees',{'base_tree':base,'tree':tree})
    commit=api('git/commits',{'message':'Document verified 160-run pilot and add paper, Overleaf source and evidence',
                            'tree':created_tree['sha'],'parents':[parent]})
    if api('git/ref/heads/main')['object']['sha']!=parent:
        raise RuntimeError('main moved during preparation; refused to overwrite concurrent work')
    api('git/refs/heads/main',{'sha':commit['sha'],'force':False},method='PATCH')
    verified=api('git/ref/heads/main')['object']['sha']
    if verified!=commit['sha']:
        raise RuntimeError('Remote ref verification failed')
    receipt={'branch':'main','commit':verified,'parent':parent,'sha256':hashes,
             'url':'https://github.com/alpha08-prog/Cloud_Security/commit/'+verified}
    (scratch/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['url'])


if __name__=='__main__':
    main()
