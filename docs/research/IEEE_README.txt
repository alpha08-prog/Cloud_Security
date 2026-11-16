IsoLab IEEE conference manuscript

Authors
Atharva Agrawal, 23bds010@iiitdwd.ac.in
Niti Priya, 23bcs087@iiitdwd.ac.in
Indian Institute of Information Technology Dharwad, Dharwad, India

Authoritative manuscript: IsoLab_IEEE.tex
Final paper: IsoLab_Research_Paper.pdf
Vector figures: ieee-architecture.pdf and ieee-latency.pdf

Format
The source uses the official IEEEtran class in conference mode on US Letter paper.
It uses standard class typography, a two-column body, author blocks, abstract,
IEEE keywords, numbered sections and equations, table captions above tables,
figure captions below figures, and numbered references. No publication identifier,
acceptance statement, funding claim, or copyright notice has been invented.

Build in Overleaf
Upload IsoLab_IEEE.tex and both vector figure PDFs to a project and select
IsoLab_IEEE.tex as the main document. IEEEtran and the standard LaTeX packages
are provided by Overleaf. Compile with pdfLaTeX.

Build locally
Use a TeX installation with IEEEtran, fontenc, mathptmx, graphicx, cite,
amsmath, amssymb, array, booktabs, balance and hyperref. Run pdflatex IsoLab_IEEE.tex twice, or run
tectonic IsoLab_IEEE.tex. The builder at scripts/build_research_paper.py
regenerates the vector figures with ReportLab and invokes either compiler.

Evidence and current research basis
Horchulhack et al. (2024), DOI 10.1016/j.jnca.2024.103839, motivates resource
observation; its neural classifiers are not reproduced. Jarkas et al. (2025),
DOI 10.1145/3715001, informs selected defenses and the new startup integrity
control. Gonzalez (2012) remains historical provenance for R1-R4.
E1-E3 measurements are from the committed October 12, 2026 testbed run.
E4 configuration faults, E5 subprocess integrity challenges, and six container
integrity checks were executed on November 11, 2026. They are separate from
the historical benchmark and do not measure classifier accuracy.
The paper states its scope, limitations, unknown identity cases and unfinished
literature extension explicitly. The project artifact and evidence.json preserve
the experiment provenance and recalculated results.

Reference and figure revision on November 14, 2026
The manuscript contains 20 cited references in order of first appearance.
Blue numeric citations link to bibliography entries; each bibliography entry
has a clickable DOI or official source URL. First mentions of the principal
research authors also link directly to their source pages. Figure and table
cross-references are clickable within the PDF.
There are two figures and six tables. The comparison table separates the source
works from our evaluation. The architecture shows the separate read-only cgroup
PSI mount. The latency figure reads evidence.json, checks its E1 input hash,
and displays descriptive min-max whiskers plus the 25 ms reference target.
