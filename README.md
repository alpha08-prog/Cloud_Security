# Cloud Security Threat Lab

An interactive explorer for **Gonzalez et al. (2012), *A quantitative analysis of current
security concerns and solutions for cloud computing*** (Journal of Cloud Computing, 1:11).

The paper surveys 200+ references and counts, for each cloud-security concern, how often it
is raised versus how often a solution is proposed. Its headline finding: **virtualization is
the biggest unsolved gap — 12% of concern citations but only 3% of solution citations.**
Cross-VM / side-channel attacks sit inside that gap. This project makes the taxonomy, the
numbers, that gap, and the defenses explorable, with a conceptual cross-VM side-channel
explainer and its defenses as the centerpiece.

## Sections
- **Overview** — the concern-vs-solution thesis at a glance
- **Taxonomy explorer** — the four taxonomy trees (Figures 1–4), interactive
- **Data dashboard** — concern vs solution per category (Figures 6 & 8), radar, and the
  virtualization sub-breakdown (Figure 11)
- **Cross-VM side channels** — a labelled diagram of two co-resident VMs on shared hardware,
  a plain-English explanation of why that can leak information, and the virtualization
  defenses that address it
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

## A note on the side-channel section
The side-channel section is **explanatory and defense-focused**: a static diagram, a
conceptual explanation (co-residency plus imperfect isolation of shared hardware), and the
defenses. It contains no attack and no simulation of one. The defenses are current best
practice, not taken from the 2012 paper.

## Credit
Based on an open-access (CC BY 2.0) paper by Gonzalez et al. (2012). All concept and figure
data is attributed to that work in `docs/paper-content.md`.
