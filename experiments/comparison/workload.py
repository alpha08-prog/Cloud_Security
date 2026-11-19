"""Measured service workload, independent of classifier features and labels."""
import concurrent.futures
import hashlib
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path('/out')
kind = os.environ.get('WORKLOAD', 'payments')
stop = threading.Event()


def append(name, row):
    with (ROOT / name).open('a') as f:
        f.write(json.dumps(row) + '\n')


def cpu_work():
    start = time.perf_counter()
    value = b'isolab'
    for _ in range(2500):
        value = hashlib.sha256(value).digest()
    return 1000 * (time.perf_counter() - start)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        value = cpu_work() if self.path == '/work' else 0
        body = json.dumps({'workMs': value}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def spark():
    from pyspark.ml.classification import LinearSVC, RandomForestClassifier
    from pyspark.ml.feature import VectorAssembler
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as f
    session = (SparkSession.builder.master('local[2]').appName('isolab-comparison')
               .config('spark.ui.enabled', 'false').config('spark.driver.memory', '768m')
               .config('spark.sql.shuffle.partitions', '2').getOrCreate())
    session.sparkContext.setLogLevel('ERROR')
    data = session.range(int(os.environ.get('SPARK_ROWS', '20000')))
    columns = [f'f{i}' for i in range(8)]
    for i, col in enumerate(columns):
        data = data.withColumn(col, f.rand(100 + i))
    data = data.withColumn('label', (f.col('f0') + f.col('f1') > 1).cast('double'))
    data = VectorAssembler(inputCols=columns, outputCol='features').transform(data).select('features', 'label').cache()
    data.count()
    (ROOT / 'ready').write_text('ready')
    job = 0
    while not (ROOT / 'stop').exists():
        model = RandomForestClassifier(numTrees=10, maxDepth=5, seed=42) if kind == 'rf' else LinearSVC(maxIter=10)
        start = time.time()
        model.fit(data)
        append('jobs.jsonl', {'job': job, 'started': start, 'ended': time.time(),
                              'durationMs': (time.time() - start) * 1000})
        job += 1
    session.stop()


def noise_worker(_=None):
    # Completed hash batches provide a workload-specific background throughput measure.
    value = b'background'
    while not (ROOT / 'stop').exists():
        start = time.time()
        for _ in range(100000):
            value = hashlib.sha256(value).digest()
        append(f'noise-{os.getpid()}.jsonl', {'ended': time.time(), 'batches': 1, 'seconds': time.time() - start})


if __name__ == '__main__':
    ROOT.mkdir(exist_ok=True)
    if kind == 'noise':
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
            list(pool.map(noise_worker, range(8)))
    elif kind == 'payments':
        (ROOT / 'ready').write_text('ready')
        ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
    else:
        spark()
