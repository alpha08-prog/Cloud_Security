// One-line explanations for the virtualization controls in src/data/defenses.ts.
// These are standard best-practice descriptions, not content from the paper, and
// are keyed by the control text so the defense list itself stays in src/data.

export type DefenseAim = 'Avoids co-residency' | 'Strengthens isolation' | 'Removes the signal'

export interface DefenseNote {
  prevents: string
  aim: DefenseAim
}

export const VIRTUALIZATION_DEFENSE_NOTES: Readonly<Record<string, DefenseNote>> = {
  'Dedicated / bare-metal instances to avoid co-residency': {
    prevents:
      'No other tenant shares the physical CPU, caches or memory, so there is no neighbour to learn from.',
    aim: 'Avoids co-residency',
  },
  'Placement hardening so an attacker can’t force co-location': {
    prevents:
      'Stops a tenant from deliberately steering its VMs onto the same host as a chosen target.',
    aim: 'Avoids co-residency',
  },
  'Cache partitioning (e.g. Intel CAT) and page coloring': {
    prevents:
      'Gives each tenant its own slice of the shared cache, so one tenant’s activity no longer disturbs another’s.',
    aim: 'Strengthens isolation',
  },
  'Constant-time cryptography': {
    prevents:
      'Crypto code behaves the same whatever the key, so its use of shared hardware reveals nothing about secrets.',
    aim: 'Removes the signal',
  },
  'Disable SMT/hyper-threading for sensitive workloads': {
    prevents:
      'Two tenants’ threads can no longer run on one physical core at once and share its per-core resources.',
    aim: 'Strengthens isolation',
  },
  'Minimal, promptly patched hypervisor (small TCB)': {
    prevents:
      'Less code enforcing isolation means fewer hypervisor flaws that could let one VM reach another.',
    aim: 'Strengthens isolation',
  },
  'Scrub memory on deallocation': {
    prevents:
      'Memory released by one tenant is wiped before another receives it, so no residual data is left behind.',
    aim: 'Strengthens isolation',
  },
}
