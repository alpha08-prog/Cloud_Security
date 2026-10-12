// E1 load: an open-model (constant-arrival-rate) workload against tenant-a /work.
//
// Open model: requests are sent on schedule whether or not earlier ones have
// returned, so a slow server cannot slow down the load generator and hide its
// own latency (no "coordinated omission"). If k6 runs out of VUs it records
// dropped_iterations, and the run is then invalid (docs/experiments.md).
//
// The output is a single JSON document on stdout (see handleSummary).
import http from 'k6/http'
import { Trend } from 'k6/metrics'

const TARGET = __ENV.TARGET || 'http://tenant-a:8080/work'
const RATE = Number(__ENV.RATE || 50)
const WARMUP = __ENV.WARMUP || '15s'
const DURATION = __ENV.DURATION || '90s'

const serverWork = new Trend('server_work_ms', true)

function seconds(d) {
  return Number(String(d).replace('s', ''))
}

export const options = {
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    warmup: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: WARMUP,
      preAllocatedVUs: 20,
      maxVUs: 200,
      gracefulStop: '0s',
    },
    measure: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      startTime: `${seconds(WARMUP)}s`,
      duration: DURATION,
      preAllocatedVUs: 20,
      maxVUs: 200,
    },
  },
  // Thresholds that always pass, declared only so k6 reports the
  // measure-scenario sub-metrics separately from the warm-up.
  thresholds: {
    'http_req_duration{scenario:measure}': ['max>=0'],
    'http_req_failed{scenario:measure}': ['rate>=0'],
    'server_work_ms{scenario:measure}': ['max>=0'],
    'dropped_iterations{scenario:measure}': ['count>=0'],
    'iterations{scenario:measure}': ['count>=0'],
  },
}

export default function () {
  const res = http.get(TARGET, { timeout: '10s' })
  const timing = res.headers['Server-Timing'] || ''
  const match = /dur=([0-9.]+)/.exec(timing)
  if (match) serverWork.add(Number(match[1]))
}

export function handleSummary(data) {
  const pick = (name) => (data.metrics[name] ? data.metrics[name].values : null)
  const doc = {
    target: TARGET,
    rate: RATE,
    warmup: WARMUP,
    duration: DURATION,
    latencyMs: pick('http_req_duration{scenario:measure}'),
    serverWorkMs: pick('server_work_ms{scenario:measure}'),
    failedRate: (pick('http_req_failed{scenario:measure}') || { rate: 0 }).rate,
    droppedIterations: (pick('dropped_iterations{scenario:measure}') || { count: 0 }).count,
    iterations: (pick('iterations{scenario:measure}') || { count: 0 }).count,
  }
  return { stdout: JSON.stringify(doc) }
}
