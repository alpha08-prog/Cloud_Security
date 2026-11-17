import study from '../../../results/research/study.json'
import paperUrl from '../../../docs/research/IsoLab_Research_Paper.pdf?url'
import '../system/System.css'

export function Research() {
  return (
    <div className="system">
      <section className="card system__block">
        <h3 className="card__title">Two recent papers, one evaluated implementation</h3>
        <p><a href={paperUrl} download="IsoLab_Research_Paper.pdf">Download the revised IEEE research paper</a></p>
        <p><a href={study.sources.qos2024}>Horchulhack et al. (2024)</a> motivates provider-side
          observation of multi-tenant interference. IsoLab measures CPU pressure and request latency,
          using explicit rules and resource controls. Its autoencoder and RNN are future work.</p>
        <p><a href={study.sources.security2025}>Jarkas et al. (ACM, 2025)</a> supplies the security
          taxonomy. We implement selected defenses: restricted host mounts, read-only filesystems,
          least privilege, namespaces, syscall filtering and resource limits. A new startup control
          hashes allowlisted executables and entry scripts before allowing a hardened workload to run.</p>
        <p>The contribution is an executable connection between selected survey defenses, configuration
          checks, startup enforcement and reliability evidence. This is a scoped engineering extension;
          no superiority over either paper’s detector or complete taxonomy coverage is established.</p>
      </section>
      <section className="card system__block">
        <h3 className="card__title">ACM defense evidence</h3>
        <p>Pass means every mapped configuration check passed without a waiver. Runtime and boundary
          references identify complementary experiments, not proof against all exploits in that category.</p>
        <p>Four hardened themes are verified. Documented provider exceptions keep the mount and
          privilege themes unverified under this strict all-target rule.</p>
        <div className="data-table__wrap"><table className="data-table data-table--prose">
          <thead><tr><th>Selected theme</th><th>Source association</th><th>Checks</th><th>Insecure</th><th>Hardened</th></tr></thead>
          <tbody>{study.themes.map(t => <tr key={t.id}>
            <th>{t.title}</th><td>{t.source}</td><td>{t.checks.join(', ')}</td>
            <td>{t.profiles.insecure.configurationVerified ? 'Verified' : 'Unverified'}</td>
            <td>{t.profiles.hardened.configurationVerified ? 'Verified' : 'Unverified'}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
      <section className="card system__block">
        <h3 className="card__title">E4: {study.e4.detected}/{study.e4.total} configuration faults detected</h3>
        <p>Each fault is applied to a fresh copy of the saved hardened snapshot. A passing baseline
          must become an explicit failure on tenant A. No deployed container is weakened.</p>
        <div className="data-table__wrap"><table className="data-table">
          <thead><tr><th>Fault</th><th>Mutation</th><th>Check</th><th>Before</th><th>After</th></tr></thead>
          <tbody>{study.e4.cases.map(r => <tr key={r.id}>
            <th>{r.id}</th><td>{r.mutation}</td><td>{r.check}</td><td>{r.baseline}</td><td>{r.mutated}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
      <section className="card system__block">
        <h3 className="card__title">E5: startup integrity enforcement</h3>
        <p>The clean application executes. Altered, missing or unlisted scripts and an invalid manifest
          are refused with exit code 78 before the application executes. This implements a selected
          startup aspect of ACM mitigation M2. The builder, launcher and manifest are trusted.</p>
        <div className="data-table__wrap"><table className="data-table">
          <thead><tr><th>Challenge</th><th>Application ran</th><th>Exit</th><th>Result</th></tr></thead>
          <tbody>{study.e5.cases.map(r => <tr key={r.case}>
            <th>{r.case}</th><td>{r.executed ? 'Yes' : 'No'}</td><td>{r.exitCode}</td><td>{r.passed ? 'Pass' : 'Fail'}</td>
          </tr>)}</tbody>
        </table></div>
        <p>Reproduce: <code>python scripts/lab.py research</code>. Recorded {study.generatedAt.slice(0, 10)}.
          E1–E3 retain their original published live measurements; E4 and E5 are new local experiments.</p>
      </section>
      <section className="card system__block">
        <h3 className="card__title">Scope and future work</h3>
        <ul>{study.notImplemented.map(item => <li key={item}>{item}</li>)}</ul>
        <p>The 2012 Gonzalez survey remains historical background for R1–R4 and the original check grouping.</p>
      </section>
    </div>
  )
}
