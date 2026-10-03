# Cloud Security Threat Lab

An interactive explorer for **Gonzalez et al. (2012), *A quantitative analysis of current
security concerns and solutions for cloud computing*** (Journal of Cloud Computing, 1:11).

The paper surveys 200+ references and counts, for each cloud-security concern, how often it
is raised versus how often a solution is proposed. Its headline finding: **virtualization is
the biggest unsolved gap — 12% of concern citations but only 3% of solution citations.**
Cross-VM / side-channel attacks sit inside that gap. This project makes the taxonomy, the
numbers, that gap, and the defenses explorable, with a conceptual side-channel simulator as
the centerpiece.

## Sections
- **Overview** — the concern-vs-solution thesis at a glance
- **Taxonomy explorer** — the four taxonomy trees (Figures 1–4), interactive
- **Data dashboard** — concern vs solution per category (Figures 6 & 8), radar, and the
  virtualization sub-breakdown (Figure 11)
- **Cross-VM side-channel simulator** — a conceptual, synthetic-data visualization of how
  shared-cache timing leaks a secret, and how mitigations stop it
- **Defense matrix** — concrete modern controls answering each category of concern
- **Frameworks** — CSA, ENISA, and NIST summaries (Tables 1 & 2)

## Run locally
```bash
npm install
npm run dev
```
Build for deployment with `npm run build` (static output in `dist/`).

## Project layout
```
docs/paper-content.md   # canonical extracted content — the source of truth
CLAUDE.md               # guidance for building with Claude Code
docs/build-plan.md      # phased milestones
src/data/               # typed content mirrored from paper-content.md
src/sections/           # one folder per section
```

## A note on the simulator
The side-channel section is an **educational simulation on synthetic data**. It illustrates
the principle (co-residency → shared cache → timing leakage → secret recovery) and the
mitigations that defeat it. It performs no real timing measurement and includes no working
exploit.

## Credit
Based on an open-access (CC BY 2.0) paper by Gonzalez et al. (2012). All concept and figure
data is attributed to that work in `docs/paper-content.md`.
