import { useMediaQuery } from '../../hooks/useMediaQuery'

interface Box {
  x: number
  y: number
  w: number
  h: number
}

interface Layout {
  width: number
  height: number
  host: Box
  vmA: Box
  vmB: Box
  divider: { x: number; y1: number; y2: number }
  hypervisor: Box
  boundary: Box
  hardware: Box
  chips: [Box, Box, Box]
  /** Two wide labels need splitting onto extra lines in the tall layout. */
  tall: boolean
}

// Wide: VMs side by side above a full-width hypervisor and hardware layer.
const WIDE: Layout = {
  width: 720,
  height: 428,
  tall: false,
  host: { x: 8, y: 8, w: 704, h: 412 },
  vmA: { x: 36, y: 74, w: 300, h: 110 },
  vmB: { x: 384, y: 74, w: 300, h: 110 },
  divider: { x: 360, y1: 66, y2: 262 },
  hypervisor: { x: 36, y: 214, w: 648, h: 48 },
  boundary: { x: 24, y: 294, w: 672, h: 112 },
  hardware: { x: 36, y: 308, w: 648, h: 86 },
  chips: [
    { x: 52, y: 336, w: 196, h: 44 },
    { x: 262, y: 336, w: 196, h: 44 },
    { x: 472, y: 336, w: 196, h: 44 },
  ],
}

// Tall: the same stack, narrower, with the hardware parts stacked vertically.
const TALL: Layout = {
  width: 340,
  height: 640,
  tall: true,
  host: { x: 6, y: 6, w: 328, h: 626 },
  vmA: { x: 20, y: 72, w: 140, h: 128 },
  vmB: { x: 180, y: 72, w: 140, h: 128 },
  divider: { x: 170, y1: 64, y2: 304 },
  hypervisor: { x: 20, y: 236, w: 300, h: 68 },
  boundary: { x: 14, y: 342, w: 312, h: 276 },
  hardware: { x: 22, y: 358, w: 296, h: 248 },
  chips: [
    { x: 38, y: 396, w: 264, h: 56 },
    { x: 38, y: 464, w: 264, h: 56 },
    { x: 38, y: 532, w: 264, h: 56 },
  ],
}

const LINE = 18

/** Lines of text centred in a box. */
function BoxText({ box, lines, className }: { box: Box; lines: string[]; className: string }) {
  const cx = box.x + box.w / 2
  const top = box.y + box.h / 2 - ((lines.length - 1) * LINE) / 2
  return (
    <text className={className} x={cx} y={top} textAnchor="middle" dominantBaseline="middle">
      {lines.map((line, i) => (
        <tspan key={line} x={cx} dy={i === 0 ? 0 : LINE}>
          {line}
        </tspan>
      ))}
    </text>
  )
}

/** Two-tone label: a title line then muted detail lines. */
function VmLabel({ box, title, role, detail }: { box: Box; title: string; role: string; detail: string[] }) {
  const cx = box.x + box.w / 2
  const lines = 2 + detail.length
  const top = box.y + box.h / 2 - ((lines - 1) * LINE) / 2
  return (
    <text x={cx} y={top} textAnchor="middle" dominantBaseline="middle">
      <tspan className="dg-title" x={cx}>
        {title}
      </tspan>
      <tspan className="dg-role" x={cx} dy={LINE}>
        {role}
      </tspan>
      {detail.map((d) => (
        <tspan key={d} className="dg-sub" x={cx} dy={LINE}>
          {d}
        </tspan>
      ))}
    </text>
  )
}

function Arrow({ x, y1, y2 }: { x: number; y1: number; y2: number }) {
  return <line className="dg-link" x1={x} y1={y1} x2={x} y2={y2} markerEnd="url(#dg-arrow)" />
}

/**
 * Static, conceptual diagram: two co-resident tenant VMs on one physical host.
 * The hypervisor separates them logically; the hardware beneath is shared.
 */
export function HostDiagram() {
  const narrow = useMediaQuery('(max-width: 640px)')
  const L = narrow ? TALL : WIDE
  const { host, vmA, vmB, divider, hypervisor, boundary, hardware, chips } = L
  const legendWidth = L.tall ? 272 : 318

  return (
    <svg
      className="host-diagram"
      viewBox={`0 0 ${L.width} ${L.height}`}
      role="img"
      aria-labelledby="dg-title dg-desc"
    >
      <title id="dg-title">Two co-resident tenant VMs on one physical host</title>
      <desc id="dg-desc">
        A physical host runs a hypervisor with two tenant virtual machines on it: tenant A (the
        victim) and tenant B (the attacker). A dashed divider shows the logical isolation the
        hypervisor provides between them. Beneath the hypervisor both VMs use the same physical
        hardware — CPU cores, a shared last-level cache, and memory — which is marked as the trust
        boundary that isolation is meant to enforce.
      </desc>
      <defs>
        <marker
          id="dg-arrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path className="dg-arrowhead" d="M0 0 L10 5 L0 10 z" />
        </marker>
      </defs>

      {/* Host */}
      <rect className="dg-host" x={host.x} y={host.y} width={host.w} height={host.h} rx={14} />
      <text className="dg-caption" x={host.x + 16} y={host.y + 26}>
        {L.tall ? 'Physical host (one server)' : 'Physical host — one server in the provider’s data centre'}
      </text>

      {/* Logical isolation between the VMs */}
      <line className="dg-divider" x1={divider.x} y1={divider.y1} x2={divider.x} y2={divider.y2} />
      <text className="dg-divider-label" x={divider.x} y={divider.y1 - 8} textAnchor="middle">
        logical isolation
      </text>

      {/* Tenant VMs */}
      <rect className="dg-vm dg-vm--a" x={vmA.x} y={vmA.y} width={vmA.w} height={vmA.h} rx={10} />
      <VmLabel
        box={vmA}
        title="Tenant A"
        role="victim VM"
        detail={L.tall ? ['own guest OS', '+ workloads'] : ['own guest OS and workloads']}
      />
      <rect className="dg-vm dg-vm--b" x={vmB.x} y={vmB.y} width={vmB.w} height={vmB.h} rx={10} />
      <VmLabel
        box={vmB}
        title="Tenant B"
        role="attacker VM"
        detail={L.tall ? ['own guest OS', '+ workloads'] : ['own guest OS and workloads']}
      />

      {/* Both VMs run through the hypervisor onto the same hardware */}
      <Arrow x={vmA.x + vmA.w / 2} y1={vmA.y + vmA.h} y2={hypervisor.y - 2} />
      <Arrow x={vmB.x + vmB.w / 2} y1={vmB.y + vmB.h} y2={hypervisor.y - 2} />
      <Arrow x={vmA.x + vmA.w / 2} y1={hypervisor.y + hypervisor.h} y2={hardware.y - 2} />
      <Arrow x={vmB.x + vmB.w / 2} y1={hypervisor.y + hypervisor.h} y2={hardware.y - 2} />

      <rect
        className="dg-hypervisor"
        x={hypervisor.x}
        y={hypervisor.y}
        width={hypervisor.w}
        height={hypervisor.h}
        rx={8}
      />
      <BoxText
        box={hypervisor}
        className="dg-title"
        lines={
          L.tall
            ? ['Hypervisor', 'separates VMs’ memory', 'and execution']
            : ['Hypervisor — separates the VMs’ memory and execution']
        }
      />

      {/* Shared hardware = trust boundary */}
      <rect
        className="dg-boundary"
        x={boundary.x}
        y={boundary.y}
        width={boundary.w}
        height={boundary.h}
        rx={12}
      />
      <rect
        className="dg-hardware"
        x={hardware.x}
        y={hardware.y}
        width={hardware.w}
        height={hardware.h}
        rx={8}
      />
      <text
        className="dg-title"
        x={hardware.x + hardware.w / 2}
        y={hardware.y + 16}
        textAnchor="middle"
        dominantBaseline="middle"
      >
        Shared physical hardware
      </text>
      {chips.map((chip, i) => (
        <rect
          key={i}
          className={i === 1 ? 'dg-chip dg-chip--cache' : 'dg-chip'}
          x={chip.x}
          y={chip.y}
          width={chip.w}
          height={chip.h}
          rx={6}
        />
      ))}
      <BoxText box={chips[0]} className="dg-sub dg-sub--strong" lines={['CPU cores', '(incl. SMT threads)']} />
      <BoxText box={chips[1]} className="dg-sub dg-sub--strong" lines={['Shared last-level', 'CPU cache']} />
      <BoxText box={chips[2]} className="dg-sub dg-sub--strong" lines={['Memory and', 'memory bus']} />

      {/* Trust-boundary legend sits on the outline's bottom edge, clear of the arrows */}
      <rect
        className="dg-legend-bg"
        x={boundary.x + 14}
        y={boundary.y + boundary.h - 11}
        width={legendWidth}
        height={22}
        rx={4}
      />
      <text
        className="dg-boundary-label"
        x={boundary.x + 22}
        y={boundary.y + boundary.h}
        dominantBaseline="middle"
      >
        {L.tall ? 'Trust boundary: isolation must hold' : 'Trust boundary — isolation must hold here'}
      </text>
    </svg>
  )
}
