"""Apply the completed-pilot narrative without editing measurements."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'docs/research/IsoLab_IEEE.tex'
text=path.read_text(encoding='utf-8')
if r'\input{pilot-section.tex}' in text:
    raise SystemExit('Pilot narrative already applied')
abstract='''Multi-tenant containers require both enforceable boundaries and predictable resource access. IsoLab integrates thirty configuration checks, resource controls, event rules and startup-integrity enforcement with a reproducible interference evaluation. A new single-host pilot comprises 160 runs of a payments service and Spark RandomForest and SVM workloads. Under sustained contention, the hardened resource-control adaptation reduces median victim latency or job time by 61.0, 35.1 and 40.1 percent, respectively, while reducing competing-workload throughput by approximately 64--66 percent. Using common telemetry and execution-level held-out splits, a lightweight resource-logistic detector achieves F1 1.000 versus 0.941 for a 2024-inspired autoencoder/LSTM adaptation on payments; both reach 1.000 on RandomForest. On SVM, logistic F1 is 0.400 versus 0.857 for the neural adaptation. Logistic fitting takes milliseconds rather than tens of seconds, but accuracy depends on workload and the small test sets do not establish general superiority. Historical security experiments additionally validate twelve blocked exposure paths, independent configuration faults and startup-integrity decisions. The contribution is a reproducible evaluation of isolation benefits, resource cost and detector tradeoffs, with explicit separation between published reference numbers and locally measured adaptations.'''
text=re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}',lambda m:r'\begin{abstract}'+'\n'+abstract+'\n'+r'\end{abstract}',text,flags=re.S)
text=text.replace('The study addresses four research questions:', 'The study addresses five research questions:')
needle=r'\item \textbf{RQ4:} Do selected defense checks and startup integrity enforcement reject their specified configuration and file-integrity faults?'
text=text.replace(needle,needle+'\n'+r'\item \textbf{RQ5:} How do a lightweight resource classifier, a 2024-inspired temporal model and existing rules trade detection quality against fitting cost on common measurements?')
text=text.replace('Our contributions are: (1)', 'Our contributions are: (1) a 160-run matched pilot comparing interference protection, competing throughput and detector accuracy/cost on three workloads; (2)',1)
text=text.replace('; (2) startup hashing','; (3) startup hashing',1).replace('; (3) independent configuration-fault','; (4) independent configuration-fault',1).replace('; and (4) fail-closed','; and (5) fail-closed',1)
text=text.replace('It does not reproduce the autoencoder, recurrent neural network, or four-host Kubernetes/Spark evaluation.', 'The new pilot implements an explicit single-host architecture adaptation using common local telemetry, not the original four-host feature pipeline or deployment.')
text=text.replace('Distributed-service interference detection; motivates our deterministic monitoring adaptation','Distributed-service interference detection; principal quantitative reference')
text=text.replace('Local E1--E3 comparison plus E4--E5 challenges; no classifier superiority claim','E1--E5 evidence and a 160-run matched adaptation; workload-dependent results')
text=text.replace('No comparative benchmark against that defense, commercial security products, or alternative detectors was performed.', 'No comparative benchmark against that scheduler or commercial security products was performed; the later pilot compares four detection approaches on common telemetry.')
text=text.replace('There is no head-to-head comparison with the 2024 learned classifier and no basis for a claim of greater accuracy or comprehensive security than either source paper.', r'The separate pilot in Section~\ref{sec:pilot} compares a locally adapted neural architecture with alternative detectors. Its workload-dependent findings do not establish general superiority over the source paper or broader security.')
text=text.replace('The present study does not measure consolidation efficiency or cost, so the latency improvement should not be interpreted as a cost-free optimization.', 'The new pilot measures competing-workload throughput but not economic consolidation cost; its latency improvements must be read alongside the observed throughput reduction.')
text=text.replace('The revised Python suite reports 182 passed and one skipped test;', 'Previously reported software validation recorded 182 Python tests passed and one skipped;')
text=text.replace('The frontend reports 52 passing tests. Lint and the production build pass.', 'That revision also recorded 52 frontend tests passing, together with lint and production-build checks. The pilot adds five comparison-utility tests, a model forward/backward smoke check, and independent recalculation of all 160 run summaries and twelve detector/workload results.')
text=text.replace('The evaluation uses one machine, a synthetic service, fixed offered load, three repetitions per arm, and short observation windows.', 'Historical E1 uses one machine, a synthetic service, fixed offered load and three repetitions per arm. The new pilot extends to three workloads with ten runs per cell, but retains one host and short observation windows.')
text=text.replace('No independent baseline tool was benchmarked.', 'The pilot implements baselines locally; it does not benchmark the source authors\' released executable or a production security tool.')
text=text.replace('Request-level load-test traces and full monitoring time series are absent from the committed published package, limiting reconstruction to supplied summaries and outcomes.', 'Historical E1 lacks request-level traces in its published package. The new pilot retains request records, Spark job logs, telemetry, execution splits, predictions and model artifacts; its source hashes and manifest identify the local experimental revision.')
text=text.replace('IsoLab & -- & -- & -- & -- \\\n','')
text=text.replace('Dashes mean no matched classifier evaluation.\nThe original distributed Spark testbed differs from our single-host payments workload.', r'These are published source values. Our measured single-host adaptation is reported separately in Table~\ref{tab:pilot}; the experimental conditions differ.')
text=text.replace('Matched prediction study pending', 'Measured single-host architecture adaptation')
text=text.replace('Historical local evidence; no classifier ranking', 'Historical security evidence and matched pilot tradeoffs')
start=text.index(r'\subsection{Matched-Comparison Protocol and Claim Gate}')
end=text.index(r'\balance',start)
text=text[:start]+r'\input{pilot-section.tex}'+'\n\n'+text[end:]
start=text.index(r'\section{Conclusion and Future Work}')
end=text.index(r'\begin{thebibliography}',start)
conclusion=r'''\section{Conclusion and Future Work}
IsoLab connects container controls to reproducible security and reliability evidence.
The completed 160-run pilot demonstrates 61.0\%, 35.1\% and 40.1\% reductions in
victim time under sustained contention for payments, Spark RF and Spark SVM,
respectively. These gains accompany approximately 64--66\% lower competing
throughput, making the allocation tradeoff explicit. The lightweight detector
has a higher payments F1 point estimate and ties RF at much lower measured fitting
cost than the neural adaptation, but loses accuracy on SVM. The complete comparison
supports workload-specific engineering choices, not universal classifier superiority.

Historical experiments additionally demonstrate the tested boundary, configuration
and startup-integrity outcomes. Together, the artifacts provide a basis for evaluating
controls and detection on common evidence without conflating posture scores,
trigger acceptance, classifier accuracy or published literature statistics.
Future work should add independent workloads and hosts, longer observation,
monitoring-disabled measurements, individual-control ablations and robust
validation-selected operating points. Signed manifests, continuous integrity
observation and broader exploit-based validation remain separate extensions.

'''
text=text[:start]+conclusion+text[end:]
text=text.replace('integrity and fault studies Nov. 11, 2026.', 'integrity and fault studies Nov. 11, 2026; matched pilot Nov. 17, 2026.')
path.write_text(text,encoding='utf-8')
