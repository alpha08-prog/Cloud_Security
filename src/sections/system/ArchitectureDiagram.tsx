import '../../components/diagram.css'
import { E1 } from '../../data/results'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import './ArchitectureDiagram.css'

interface Box {
  x: number
  y: number
  w: number
  h: number
}

type Kind = 'tenant' | 'engine' | 'chip' | 'decoy' | 'hardware'

interface Node {
  id: string
  box: Box
  kind: Kind
  title: string
  lines: string[]
  badges?: string[]
}

interface Layout {
  width: number
  height: number
  host: Box
  provider: Box
  nodes: Node[]
  arrows: { from: [number, number]; to: [number, number] }[]
}

const place = E1.environment.placement
/** "4,5" -> "4–5", "6,7,8,9" -> "6–9", "0,2" -> "0, 2". */
function cores(key: string): string {
  const ids = (place[key] ?? '').split(',').filter(Boolean).map(Number)
  if (!ids.length) return '?'
  const runs: string[] = []
  let start = ids[0]
  let prev = ids[0]
  for (const id of [...ids.slice(1), NaN]) {
    if (id === prev + 1) {
      prev = id
      continue
    }
    runs.push(start === prev ? `${start}` : `${start}–${prev}`)
    start = prev = id
  }
  return runs.join(', ')
}
const HW = `provider ${cores('CPUSET_PROVIDER')} · load gen ${cores('CPUSET_LOADGEN')} · A ${cores('CPUSET_TENANT_A')} · B ${cores('CPUSET_TENANT_B')} · C ${cores('CPUSET_TENANT_C')}`
const HW_TITLE = `CPU: ${E1.environment.physicalCores} physical cores × ${
  E1.environment.logicalCpus / Math.max(1, E1.environment.physicalCores)
} SMT threads`

function tenants(boxes: [Box, Box, Box], compact: boolean): Node[] {
  return [
    {
      id: 'a',
      box: boxes[0],
      kind: 'tenant',
      title: 'Tenant A · payments-api',
      lines: compact ? ['victim in E1', `cores ${cores('CPUSET_TENANT_A')} · net-a · own volume`] : ['victim in E1', `cores ${cores('CPUSET_TENANT_A')} · net-a · a-data`],
      badges: ['R1', 'R2'],
    },
    {
      id: 'b',
      box: boxes[1],
      kind: 'tenant',
      title: 'Tenant B · batch-analytics',
      lines: ['+ noisy stress-ng job (E1)', `cores ${cores('CPUSET_TENANT_B')} · net-b · b-data`],
      badges: ['R1', 'R2'],
    },
    {
      id: 'c',
      box: boxes[2],
      kind: 'tenant',
      title: 'Tenant C · legacy-app',
      lines: ['probe source in E2', `cores ${cores('CPUSET_TENANT_C')} · net-c · c-data`],
      badges: ['R1', 'R2'],
    },
  ]
}

const WIDE: Layout = (() => {
  const t: [Box, Box, Box] = [
    { x: 24, y: 52, w: 228, h: 96 },
    { x: 266, y: 52, w: 228, h: 96 },
    { x: 508, y: 52, w: 228, h: 96 },
  ]
  const proxy = { x: 40, y: 280, w: 150, h: 64 }
  const auditor = { x: 210, y: 280, w: 236, h: 64 }
  const prom = { x: 466, y: 280, w: 122, h: 64 }
  const graf = { x: 604, y: 280, w: 116, h: 64 }
  const canary = { x: 210, y: 362, w: 236, h: 40 }
  return {
    width: 760,
    height: 512,
    host: { x: 8, y: 8, w: 744, h: 496 },
    provider: { x: 24, y: 236, w: 712, h: 180 },
    nodes: [
      ...tenants(t, false),
      {
        id: 'engine',
        box: { x: 24, y: 166, w: 712, h: 50 },
        kind: 'engine',
        title: 'Container engine + one shared Linux kernel: the testbed’s “hypervisor”',
        lines: ['namespaces · cgroups v2 (CPU, memory, PIDs, PSI) · seccomp · capabilities'],
      },
      { id: 'proxy', box: proxy, kind: 'chip', title: 'socket-proxy', lines: ['read-only engine API'] },
      {
        id: 'auditor',
        box: auditor,
        kind: 'chip',
        title: 'cloudaudit',
        lines: ['30 checks · PSI exporter · event watcher'],
        badges: ['R1', 'R3', 'R4'],
      },
      { id: 'prom', box: prom, kind: 'chip', title: 'Prometheus', lines: ['alert rules'], badges: ['R3'] },
      { id: 'graf', box: graf, kind: 'chip', title: 'Grafana', lines: ['live view'] },
      { id: 'canary', box: canary, kind: 'decoy', title: 'canary “metadata” decoy', lines: [], badges: ['R4'] },
      { id: 'hw', box: { x: 24, y: 432, w: 712, h: 56 }, kind: 'hardware', title: HW_TITLE, lines: [HW] },
    ],
    arrows: [
      { from: [proxy.x + proxy.w, proxy.y + 32], to: [auditor.x - 2, auditor.y + 32] },
      { from: [auditor.x + auditor.w, auditor.y + 32], to: [prom.x - 2, prom.y + 32] },
      { from: [prom.x + prom.w, prom.y + 32], to: [graf.x - 2, graf.y + 32] },
      { from: [canary.x + canary.w / 2, canary.y], to: [auditor.x + auditor.w / 2, auditor.y + auditor.h + 2] },
    ],
  }
})()

const TALL: Layout = (() => {
  const t: [Box, Box, Box] = [
    { x: 18, y: 48, w: 324, h: 82 },
    { x: 18, y: 140, w: 324, h: 82 },
    { x: 18, y: 232, w: 324, h: 82 },
  ]
  const chip = (y: number, h = 52): Box => ({ x: 34, y: y + 8, w: 292, h })
  return {
    width: 360,
    height: 884,
    host: { x: 6, y: 6, w: 348, h: 872 },
    provider: { x: 18, y: 418, w: 324, h: 346 },
    nodes: [
      ...tenants(t, true),
      {
        id: 'engine',
        box: { x: 18, y: 330, w: 324, h: 72 },
        kind: 'engine',
        title: 'Engine + shared kernel',
        lines: ['the testbed’s “hypervisor”', 'namespaces · cgroups v2 · seccomp'],
      },
      { id: 'proxy', box: chip(452), kind: 'chip', title: 'socket-proxy', lines: ['read-only engine API'] },
      {
        id: 'auditor',
        box: chip(516, 64),
        kind: 'chip',
        title: 'cloudaudit',
        lines: ['checks · PSI exporter', 'event watcher'],
        badges: ['R1', 'R3', 'R4'],
      },
      { id: 'canary', box: chip(592, 44), kind: 'decoy', title: 'canary “metadata” decoy', lines: [], badges: ['R4'] },
      { id: 'prom', box: chip(648, 44), kind: 'chip', title: 'Prometheus · alert rules', lines: [], badges: ['R3'] },
      { id: 'graf', box: chip(702, 44), kind: 'chip', title: 'Grafana · live view', lines: [] },
      {
        id: 'hw',
        box: { x: 18, y: 778, w: 324, h: 86 },
        kind: 'hardware',
        title: HW_TITLE,
        lines: [
          `provider ${cores('CPUSET_PROVIDER')} · load gen ${cores('CPUSET_LOADGEN')}`,
          `A ${cores('CPUSET_TENANT_A')} · B ${cores('CPUSET_TENANT_B')} · C ${cores('CPUSET_TENANT_C')}`,
        ],
      },
    ],
    arrows: [],
  }
})()

const LINE = 17

function NodeView({ node }: { node: Node }) {
  const { box, title, lines, badges } = node
  const cx = box.x + box.w / 2
  const total = 1 + lines.length
  const top = box.y + box.h / 2 - ((total - 1) * LINE) / 2
  return (
    <g>
      <rect className={`ar-${node.kind}`} x={box.x} y={box.y} width={box.w} height={box.h} rx={8} />
      <text x={cx} y={top} textAnchor="middle" dominantBaseline="middle">
        <tspan className="dg-title" x={cx}>
          {title}
        </tspan>
        {lines.map((l) => (
          <tspan key={l} className="dg-sub" x={cx} dy={LINE}>
            {l}
          </tspan>
        ))}
      </text>
      {badges?.map((b, i) => {
        const bx = box.x + box.w - 6 - (badges.length - i) * 28
        return (
          <g key={b}>
            <rect className="ar-badge" x={bx} y={box.y - 9} width={24} height={18} rx={9} />
            <text className="ar-badge-text" x={bx + 12} y={box.y} textAnchor="middle" dominantBaseline="middle">
              {b}
            </text>
          </g>
        )
      })}
    </g>
  )
}

/** The IsoLab testbed: tenants, the shared engine/kernel, the provider plane and the CPU layout. */
export function ArchitectureDiagram() {
  const narrow = useMediaQuery('(max-width: 640px)')
  const L = narrow ? TALL : WIDE
  return (
    <svg
      className="diagram arch-diagram"
      viewBox={`0 0 ${L.width} ${L.height}`}
      role="img"
      aria-labelledby="ar-title ar-desc"
    >
      <title id="ar-title">IsoLab testbed architecture</title>
      <desc id="ar-desc">
        One container host runs three tenants (A payments-api, B batch-analytics with a noisy job, C
        legacy-app), each with its own CPU cores, internal network and volume. They share one container
        engine and Linux kernel. A provider plane, identical in both profiles, contains a read-only socket
        proxy, the cloudaudit auditor (checks, pressure exporter, event watcher), a decoy metadata canary,
        Prometheus and Grafana. The CPU layout at the bottom shows which physical cores each role uses.
      </desc>
      <defs>
        <marker id="ar-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path className="dg-arrowhead" d="M0 0 L10 5 L0 10 z" />
        </marker>
      </defs>
      <rect className="dg-host" x={L.host.x} y={L.host.y} width={L.host.w} height={L.host.h} rx={14} />
      <text className="dg-caption" x={L.host.x + 16} y={L.host.y + 24}>
        {narrow ? 'Container host (one machine)' : 'Container host: one machine (Docker Desktop VM or CI runner)'}
      </text>
      <rect className="ar-provider" x={L.provider.x} y={L.provider.y} width={L.provider.w} height={L.provider.h} rx={12} />
      <text className="dg-caption" x={L.provider.x + 14} y={L.provider.y + 20}>
        {narrow ? 'Provider plane (same in both profiles)' : 'Provider plane: identical in both profiles, itself hardened'}
      </text>
      {L.arrows.map((a, i) => (
        <line
          key={i}
          className="dg-link"
          x1={a.from[0]}
          y1={a.from[1]}
          x2={a.to[0]}
          y2={a.to[1]}
          markerEnd="url(#ar-arrow)"
        />
      ))}
      {L.nodes.map((n) => (
        <NodeView key={n.id} node={n} />
      ))}
    </svg>
  )
}
