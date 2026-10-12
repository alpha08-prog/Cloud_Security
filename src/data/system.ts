// The two testbed profiles, side by side (testbed/compose.insecure.yaml vs
// testbed/compose.hardened.yaml). The provider plane is identical in both.
import type { RequirementId } from './resultTypes'

export interface ProfileRow {
  aspect: string
  insecure: string
  hardened: string
  requirement: RequirementId
}

export const PROFILE_ROWS: readonly ProfileRow[] = [
  {
    aspect: 'Network',
    insecure: 'Every tenant on one flat network with the provider plane; tenant-a also published on a host port',
    hardened: 'One internal network (no egress) per tenant; no published ports',
    requirement: 'R2',
  },
  {
    aspect: 'CPU',
    insecure: 'No limit; any tenant may run on any core',
    hardened: 'Dedicated physical cores per tenant (from the real topology) plus a CPU quota',
    requirement: 'R2',
  },
  {
    aspect: 'Memory & processes',
    insecure: 'No limits',
    hardened: 'Memory limit with no extra swap; at most 64 processes/threads',
    requirement: 'R2',
  },
  {
    aspect: 'Privileges',
    insecure: 'tenant-c privileged, in the host PID and IPC namespaces, seccomp off, root',
    hardened: 'uid 10001, all capabilities dropped, no-new-privileges, default seccomp, read-only root filesystem',
    requirement: 'R2',
  },
  {
    aspect: 'Engine access',
    insecure: 'tenant-c holds the Docker socket (control of every container)',
    hardened: 'Only the provider’s read-only socket proxy (writes rejected)',
    requirement: 'R2',
  },
  {
    aspect: 'Storage',
    insecure: 'tenant-a and tenant-c share a volume; host /etc mounted into tenant-c',
    hardened: 'One labelled volume per tenant; no host mounts',
    requirement: 'R2',
  },
  {
    aspect: 'Secrets',
    insecure: 'A password-like environment variable (dummy value)',
    hardened: 'No secrets in environment variables',
    requirement: 'R4',
  },
  {
    aspect: 'Identity',
    insecure: 'tenant-c unlabelled and built from a floating image tag',
    hardened: 'Every container, network and volume labelled; images from digest-pinned bases with revision labels',
    requirement: 'R1',
  },
]

export const RUN_COMMANDS = `python scripts/lab.py doctor             # check Docker, ports, CPU topology
python scripts/lab.py up hardened         # or: up insecure
python scripts/lab.py audit hardened      # 30 checks -> JSON + SARIF, console summary
python scripts/lab.py demo canary         # fire one benign trigger, watch the detection
python scripts/lab.py run-all             # both profiles: audit, E3, E2, E1, gates
python scripts/lab.py publish             # merge, test hypotheses, validate -> results/published
# Grafana http://127.0.0.1:3000 · Prometheus :9090 · auditor API :8088/report`
