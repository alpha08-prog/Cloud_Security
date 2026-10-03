import { DEFENSES } from '../../data/defenses'
import { getShare } from '../../data/stats'
import { UNDER_SOLVED } from '../../data/taxonomy'
import { HostDiagram } from './HostDiagram'
import { VIRTUALIZATION_DEFENSE_NOTES, type DefenseAim } from './defenseNotes'
import './SideChannel.css'

const share = getShare(UNDER_SOLVED)
const CONTROLS = DEFENSES.find((d) => d.category === UNDER_SOLVED)?.controls ?? []

const AIM_CLASS: Record<DefenseAim, string> = {
  'Avoids co-residency': 'aim--residency',
  'Strengthens isolation': 'aim--isolation',
  'Removes the signal': 'aim--signal',
}

export function SideChannel() {
  return (
    <div className="explainer">
      <p className="explainer__intro">
        In the paper’s taxonomy, <strong>isolation</strong> and <strong>cross-VM attacks</strong>{' '}
        sit in the Virtualization branch of the Architecture tree (Figure 2). Virtualization is the
        category the paper found least answered: {share.concern}% of concern citations but only{' '}
        {share.solution}% of solution citations — the largest gap of the seven. This section
        explains, conceptually, why tenants sharing one physical machine is a security concern,
        and then the defenses that address it.
      </p>

      <figure className="card explainer__figure">
        <HostDiagram />
        <figcaption className="figure-caption">
          <strong>Conceptual diagram</strong> (not a figure from the paper). The hypervisor keeps
          the two VMs apart logically, but both still run on the same physical hardware — the
          trust boundary that isolation has to enforce. “Logical isolation” and “physical
          isolation” are the two Isolation leaves in Figure 2.
        </figcaption>
      </figure>

      <section className="explainer__why" aria-labelledby="why-heading">
        <h3 id="why-heading">Why shared hardware can leak information</h3>
        <p>
          A hypervisor gives each virtual machine its own memory and its own view of the CPU, so
          one tenant cannot simply read another’s data. That is <em>logical</em> isolation. But on
          a multi-tenant host, the tenants still run on the same physical processor and share
          parts of it — most notably caches, which hold recently used data close to the CPU.
        </p>
        <p>
          Those shared parts are not fully divided between tenants, and their state is shaped by
          whatever is running. So one tenant’s activity can leave faint, indirect traces that a
          neighbour on the same machine may be able to pick up — for example, as small changes in
          how quickly its own work completes — and draw inferences from.
        </p>
        <p>
          Two conditions have to hold: <strong>co-residency</strong> (both tenants land on the same
          physical host) and <strong>imperfect isolation</strong> of the hardware they share. The
          paper lists the resulting threats under Cross-VM attacks — cryptographic key stealing,
          and VM placement / overlapping attacks. Every defense below removes one of the two
          conditions, or the secret-dependent behaviour that would otherwise be observable.
        </p>
      </section>

      <section aria-labelledby="defenses-heading">
        <h3 id="defenses-heading" className="explainer__heading">
          Defenses for virtualization
        </h3>
        <ul className="defense-cards">
          {CONTROLS.map((control) => {
            const note = VIRTUALIZATION_DEFENSE_NOTES[control]
            return (
              <li key={control} className="card defense-card">
                {note && <span className={`aim ${AIM_CLASS[note.aim]}`}>{note.aim}</span>}
                <h4 className="defense-card__title">{control}</h4>
                {note && <p className="defense-card__prevents">{note.prevents}</p>}
              </li>
            )
          })}
        </ul>
      </section>

      <p className="callout explainer__note">
        These defenses are current, published best practice — they are not taken from the 2012
        paper, which found almost no proposed solutions for this area. The control list comes from
        the project’s defense matrix (see the Defenses tab); the one-line explanations and the
        grouping are ours.
      </p>
    </div>
  )
}
