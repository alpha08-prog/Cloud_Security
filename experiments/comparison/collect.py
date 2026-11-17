"""Single-host matched-comparison collector. Runs in a host-PID Docker observer.

Only containers with the campaign's label are controlled or removed.
Raw samples and load outcomes are saved before model fitting.
"""
import argparse
from collections import deque
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import threading
import time
import urllib.request

import docker
import numpy as np
import psutil
from cloudaudit.service.stats import StatsPoller, Workload, Sample
from cloudaudit.service.detections import DetectionStore

IMAGE = 'isolab/comparison:20261117'
FEATURES = ['cpuCores', 'memoryBytes', 'pids', 'rxBytesPerSec', 'txBytesPerSec',
            'readBytesPerSec', 'writeBytesPerSec', 'throttleFraction', 'cpuPressure',
            'processCpuSeconds', 'processRss', 'processThreads', 'processReadBytes',
            'processWriteBytes', 'voluntarySwitches', 'involuntarySwitches']


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def append(path, obj):
    with path.open('a') as f:
        f.write(json.dumps(obj) + '\n')


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def sample(container, previous):
    st = container.stats(stream=False, one_shot=True)
    now = time.time()
    cpu = st['cpu_stats']['cpu_usage']['total_usage'] / 1e9
    networks = st.get('networks', {})
    rx = sum(v['rx_bytes'] for v in networks.values())
    tx = sum(v['tx_bytes'] for v in networks.values())
    io = st.get('blkio_stats', {}).get('io_service_bytes_recursive') or []
    reads = sum(v['value'] for v in io if v['op'].lower() == 'read')
    writes = sum(v['value'] for v in io if v['op'].lower() == 'write')
    throttle = st['cpu_stats'].get('throttling_data', {}).get('throttled_time', 0) / 1e9
    counters = [cpu, rx, tx, reads, writes, throttle]
    rates = [(a-b)/(now-previous['time']) for a,b in zip(counters, previous['counters'])] if previous else [0]*6
    container.reload()
    proc = psutil.Process(container.attrs['State']['Pid'])
    processes = [proc] + proc.children(recursive=True)
    totals = [0.] * 7
    for process in processes:
        try:
            ct, mem, switches = process.cpu_times(), process.memory_info(), process.num_ctx_switches()
            pi = process.io_counters()
            values = [ct.user+ct.system, mem.rss, process.num_threads(), pi.read_bytes, pi.write_bytes,
                      switches.voluntary, switches.involuntary]
            totals = [a+b for a,b in zip(totals, values)]
        except psutil.NoSuchProcess:
            continue  # transient processes may exit between enumeration and sampling
        except psutil.AccessDenied:
            raise RuntimeError('Process features unavailable; refuse silent zero imputation')
    cg = Path('/host/cgroup/docker') / container.id
    if not cg.exists():
        from cloudaudit.service.stats import find_cgroup
        cg = find_cgroup(Path('/host/cgroup'), container.id)
    pressure = 0
    if cg is None:
        raise RuntimeError('Container cgroup unavailable')
    for token in (cg / 'cpu.pressure').read_text().splitlines()[0].split():
        if token.startswith('total='):
            pressure = int(token.split('=')[1])
    pressure_rate = (pressure-previous['pressure']) / ((now-previous['time'])*1e6) if previous else 0
    # Process totals are differenced to avoid encoding run age in temporal features.
    process_features = totals[:]
    if previous:
        for i in (0,3,4,5,6):
            process_features[i] = max(0, totals[i]-previous['process'][i])/(now-previous['time'])
    else:
        for i in (0,3,4,5,6):
            process_features[i] = 0
    features = [rates[0], st['memory_stats'].get('usage', 0), st['pids_stats'].get('current', 0),
                *rates[1:5], rates[5], pressure_rate, *process_features]
    return {'time': now, 'counters': counters, 'pressure': pressure, 'process': totals,
            'features': features, 'cpuUs': int(cpu*1e6), 'psiUs': pressure}


def load(url, path, stop, rate=50):
    def request(scheduled):
        started = time.time()
        error = None
        try:
            with urllib.request.urlopen(url+'/work', timeout=3) as response:
                response.read()
        except Exception as exc:
            error = type(exc).__name__
        append(path, {'scheduled': scheduled, 'started': started, 'ended': time.time(),
                      'latencyMs': (time.time()-scheduled)*1000, 'error': error})
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        next_time = time.time()
        while not stop.is_set():
            now = time.time()
            if now < next_time:
                stop.wait(next_time-now)
                continue
            pool.submit(request, next_time)
            next_time += 1/rate


def run(client, args, spec, network):
    run_id = f"{spec['workload']}-{spec['profile']}-{spec['scenario']}-{spec['rep']:02}"
    dest = Path(args.output) / run_id
    if (dest/'result.json').exists():
        return
    if dest.exists() and any(dest.iterdir()):
        raise RuntimeError(f'Incomplete run exists at {dest}; preserve it and use a new output directory')
    dest.mkdir(parents=True, exist_ok=True)
    host_dest = args.host_workspace + '/' + str(dest.relative_to('/workspace')).replace('\\', '/')
    containers = []
    start_time = time.time()
    labels = {'io.isolab.comparison': args.campaign}
    def launch(role, workload, cpus, quota=None):
        out = dest / role
        out.mkdir(exist_ok=True)
        options = dict(image=IMAGE, command=['python', 'experiments/comparison/workload.py'],
                       detach=True, name=f'{args.campaign}-{role}', network=network.name,
                       cpuset_cpus=cpus, mem_limit='2g' if workload in ('rf','svm') else '384m',
                       volumes={args.host_workspace: {'bind':'/workspace', 'mode':'ro'},
                                host_dest+'/'+role: {'bind':'/out','mode':'rw'}},
                       environment={'WORKLOAD': workload, 'SPARK_LOCAL_IP':'127.0.0.1'},
                       labels=labels, pids_limit=512)
        if quota:
            options['nano_cpus'] = int(quota*1e9)
        if spec['profile'] == 'hardened':
            options.update(cap_drop=['ALL'], security_opt=['no-new-privileges:true'])
        c = client.containers.run(**options)
        containers.append(c)
        return c
    stopper, loader = threading.Event(), None
    try:
        separated = spec['profile'] in ('cpuset', 'hardened') or spec['scenario'] == 'benign'
        quota = 2 if spec['profile'] in ('quota','hardened') else None
        victim = launch('victim', spec['workload'], '4,5', quota)
        for _ in range(180):
            if (dest/'victim/ready').exists():
                break
            victim.reload()
            if victim.status != 'running':
                raise RuntimeError(victim.logs().decode()[-3000:])
            time.sleep(1)
        else:
            raise RuntimeError('Victim readiness timeout')
        noise = launch('noise', 'noise', '6-11' if separated else '4-11', quota)
        if spec['scenario'] == 'clean':
            noise.pause()
        if spec['workload'] == 'payments':
            victim.reload()
            ip = victim.attrs['NetworkSettings']['Networks'][network.name]['IPAddress']
            loader = threading.Thread(target=load, args=(f'http://{ip}:8080', dest/'requests.jsonl', stopper), daemon=True)
            loader.start()
        store = DetectionStore()
        detector = StatsPoller(client, store)
        detector.host_cpus = frozenset(range(12))
        for role,c,cpus in [('victim',victim,{4,5}),('noise',noise,set(range(6 if separated else 4,12)))]:
            detector.workloads[role] = Workload(role, role, 'tenant', role, c.id, int(start_time*1e9), None,
                                              frozenset(cpus), deque(maxlen=64))
        previous = {'victim':None, 'noise':None}
        measurement_start = time.time()
        samples = []
        for index in range(args.samples+1):
            target = measurement_start + index*5
            time.sleep(max(0,target-time.time()))
            if spec['scenario'] == 'bursty' and index and index%3 == 0:
                noise.reload()
                noise.unpause() if noise.attrs['State']['Paused'] else noise.pause()
            tick_cpu = time.process_time()
            values = {}
            for role,c in [('victim',victim),('noise',noise)]:
                values[role] = sample(c, previous[role])
                previous[role] = values[role]
                v = values[role]
                detector.workloads[role].history.append(Sample(t=v['time'], usage_us=v['cpuUs'], psi_cpu_us=v['psiUs']))
            detector.detect_noisy_neighbour()
            row = {'time':time.time(), 'features': values['victim']['features']+values['noise']['features'],
                   'det08': bool(store.since()), 'collectorCpuSeconds':time.process_time()-tick_cpu,
                   'collectorRss':psutil.Process().memory_info().rss}
            if index:
                samples.append(row)
                append(dest/'telemetry.jsonl', row)
        stopper.set()
        if loader:
            loader.join(timeout=5)
        end = time.time()
        requests = [r for r in read_jsonl(dest/'requests.jsonl') if r['scheduled'] >= measurement_start+10]
        jobs = [r for r in read_jsonl(dest/'victim/jobs.jsonl') if r['started'] >= measurement_start]
        performance = float(np.percentile([r['latencyMs'] for r in requests],99)) if requests else (
            statistics.median(r['durationMs'] for r in jobs) if jobs else None)
        background = sum(len(read_jsonl(p)) for p in (dest/'noise').glob('noise-*.jsonl'))
        result = dict(spec, runId=run_id, started=measurement_start, ended=end, performanceMs=performance,
                      performanceMetric='requestP99' if spec['workload']=='payments' else 'medianJobCompletion',
                      failures=sum(bool(r['error']) for r in requests), requests=len(requests), jobs=len(jobs),
                      backgroundBatchesPerSecond=background/(end-measurement_start),
                      detections=[d.model_dump(mode='json') for d in store.since()], samples=len(samples),
                      status='measured' if performance is not None else 'no-completed-job')
        save(dest/'result.json', result)
        print(json.dumps(result), flush=True)
    except Exception as exc:
        save(dest/'error.json', {'error':str(exc), 'spec':spec})
        raise
    finally:
        stopper.set()
        if loader:
            loader.join(timeout=5)
        for c in reversed(containers):
            try:
                c.reload()
                if c.attrs['State']['Paused']:
                    c.unpause()
                (dest/('victim' if c.name.endswith('victim') else 'noise')/'stop').touch()
                c.stop(timeout=5)
                (dest/(c.name+'.log')).write_bytes(c.logs())
                c.remove()
            except docker.errors.NotFound:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='/workspace/results/comparison/live')
    parser.add_argument('--host-workspace', required=True)
    parser.add_argument('--campaign', default='isolab-comparison')
    parser.add_argument('--workloads', nargs='+', default=['payments','rf','svm'])
    parser.add_argument('--profiles', nargs='+', default=['shared','quota','cpuset','hardened'])
    parser.add_argument('--scenarios', nargs='+', default=['clean','sustained','bursty','benign'])
    parser.add_argument('--repetitions', type=int, default=10)
    parser.add_argument('--samples', type=int, default=12)
    parser.add_argument('--cooldown', type=int, default=30)
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--max-hours', type=float, default=24)
    args = parser.parse_args()
    client = docker.from_env()
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    specs = [dict(workload=w, profile=p, scenario=s, rep=r) for w in args.workloads for p in args.profiles
             for s in args.scenarios for r in range(args.repetitions)]
    random.Random(20261117).shuffle(specs)
    if args.pilot:
        specs = [s for s in specs if s['profile'] in ('shared','hardened') and
                 (s['workload']=='payments' or s['scenario'] in ('clean','sustained'))]
    deadline = time.monotonic()+args.max_hours*3600
    save(dest/'manifest.json', {'schemaVersion':1, 'arguments':vars(args), 'featureNames':['victim.'+f for f in FEATURES]+['noise.'+f for f in FEATURES],
                              'imageId':client.images.get(IMAGE).id, 'environment':client.info(), 'schedule':specs,
                              'sourceHashes':{str(p.relative_to('/workspace')):hashlib.sha256(p.read_bytes()).hexdigest()
                                              for p in Path('/workspace/experiments/comparison').glob('*.py')}})
    network = client.networks.create(args.campaign, labels={'io.isolab.comparison':args.campaign})
    try:
        for spec in specs:
            if time.monotonic() > deadline:
                raise TimeoutError('Predeclared collection time budget reached; incomplete matrix retained')
            run(client,args,spec,network)
            time.sleep(args.cooldown)
    finally:
        network.remove()


if __name__ == '__main__':
    main()
