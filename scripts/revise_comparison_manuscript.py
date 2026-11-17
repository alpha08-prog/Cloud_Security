"""One-time, idempotent insertion of the sourced comparison section."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'docs/research/IsoLab_IEEE.tex'
text = path.read_text(encoding='utf-8')
section = r'''
\section{Numerical Context and Comparative Evaluation}
\label{sec:comparison}
The principal quantitative reference is the multi-tenant monitoring study
of Horchulhack et al.~\cite{qos2024}. Table~\ref{tab:published2024} records
its service-level results, preserving the workload and evaluation level.
These are published reference values, not measurements of our implementation.
IsoLab's trigger acceptance counts cannot substitute for classifier F1 or AUC:
the tests have different labels, sampling units, and negative examples.

\begin{table}[t]
\caption{Published 2024 service-classifier results (source Table 3)}
\label{tab:published2024}
\centering\small
\begin{tabular}{lrrrr}
\toprule
Spark job & TPR & TNR & AUC & F-measure \\
\midrule
RF & 0.84 & 0.89 & 0.90 & 0.90 \\
SVM & 0.87 & 0.59 & 0.82 & 0.78 \\
IsoLab & -- & -- & -- & -- \\
\bottomrule
\end{tabular}

\smallskip
\parbox{\columnwidth}{\footnotesize Dashes mean no matched classifier evaluation.
The original distributed Spark testbed differs from our single-host payments workload.}
\end{table}

\input{comparison-derived.tex}
Table~\ref{tab:derived} provides a complementary numerical view of our project.
Inflation is $100(IF-1)$; headroom is $25-q_{.99,\mathrm{noisy}}$ milliseconds.
These quantities derive from medians of the existing independent run summaries,
not additional experiments. The hardened profile has lower interference but both
profiles satisfy the latency criterion. This is an internal configuration comparison,
not a percentage improvement over the 2024 classifier.

\begin{figure*}[t]
\centering
\includegraphics[width=.92\textwidth]{ieee-comparison-runs.pdf}
\caption{Original visualization of historical IsoLab measurements. Left: every
run's request p99, three runs per arm. Right: recorded victim CPU pressure versus
p99; gray is insecure, blue is hardened, circles are clean, triangles are noisy.
Points summarize runs, not individual requests. Association does not isolate a
causal effect of CPU pressure because multiple controls change together.}
\label{fig:comparisonruns}
\end{figure*}

\subsection{Positioning Against Resource-Management Systems}
Performance isolation is already an established research problem.
PARTIES~\cite{parties} studies QoS-aware resource partitioning for colocated
interactive services. Caladan~\cite{caladan} uses fast scheduling and contention
signals, including memory-hierarchy and hyperthread interference. These studies
motivate measuring background throughput and bursty workloads alongside victim
latency: static separation may protect one workload at a utilization cost.
IsoLab does not implement their schedulers or benchmark against their published
performance numbers. Its distinction is the joint, auditable evidence for
configuration enforcement, tenant boundaries, integrity checks and interference.
That engineering integration does not establish a new scheduling algorithm.

\begin{table}[t]
\caption{Comparison scope and evidence required}
\label{tab:comparison_scope}
\centering\small
\begin{tabular}{p{.23\columnwidth}p{.32\columnwidth}p{.34\columnwidth}}
\toprule
Work & Principal mechanism & Relation to IsoLab \\
\midrule
2024 monitoring & Learned temporal detection & Matched prediction study pending \\
PARTIES & QoS-aware partitioning & Motivates throughput accounting \\
Caladan & Fast contention-aware scheduling & Motivates burst evaluation \\
IsoLab & Controls, checks and event rules & Historical local evidence; no classifier ranking \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Matched-Comparison Protocol and Claim Gate}
The accompanying dated protocol specifies a single-host adaptation with
payments and Spark RF/SVM workloads, clean and interfering conditions, and
separate quota-only, CPU-set-only and full-hardening arms. Detector comparisons
must use the same held-out telemetry and independently established degradation
labels; application latency is reserved for evaluation rather than detector input.
Training, validation and testing are split by execution, preventing neighboring
windows from leaking between partitions. Monitoring cost, false alarms, detection
delay and background throughput must be reported with run-level uncertainty.
The implementation currently supplies metric validation and architecture
scaffolding; collection, training and matched evaluation remain unfinished.
No corresponding results or improvement claim are inferred from this protocol.

'''
if r'\label{sec:comparison}' not in text:
    text = text.replace(r'\balance', section + '\n' + r'\balance', 1)
    refs = r'''
\bibitem{parties} S. Chen, C. Delimitrou, and J. F. Martinez, ``PARTIES: QoS-aware resource partitioning for multiple interactive services,'' in \emph{Proc. ASPLOS}, 2019, pp. 107--120. [Online]. Available: \url{https://doi.org/10.1145/3297858.3304005}
\bibitem{caladan} J. Fried, Z. Ruan, A. Ousterhout, and A. Belay, ``Caladan: Mitigating interference at microsecond timescales,'' in \emph{Proc. OSDI}, 2020, pp. 281--297. [Online]. Available: \url{https://www.usenix.org/conference/osdi20/presentation/fried}
'''
    text = text.replace(r'\end{thebibliography}', refs + '\n' + r'\end{thebibliography}')
    path.write_text(text, encoding='utf-8')
