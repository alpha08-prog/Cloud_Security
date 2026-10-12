import { PAPER, formatAuthors } from '../data/paper'
import './Footer.css'

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container site-footer__inner">
        <section aria-labelledby="about-heading">
          <h2 id="about-heading" className="site-footer__heading">
            About
          </h2>
          <p>
            IsoLab is a college project for a Cloud SRE &amp; Security course. It takes the one gap a
            published survey of cloud security found (virtualization isolation) and builds and
            measures the solution the paper’s future-work section describes: a multi-tenant testbed,
            an auditor, live observation and detection.
          </p>
          <p>
            Nothing here attacks anything: all validation is configuration auditing, load testing of
            the victim’s own latency, read-only reachability probes and benign detection triggers.
          </p>
        </section>

        <section aria-labelledby="sources-heading">
          <h2 id="sources-heading" className="site-footer__heading">
            Sources
          </h2>
          <p className="site-footer__citation">
            {formatAuthors(PAPER.authors)} ({PAPER.year}). <cite>{PAPER.title}</cite>.{' '}
            <i>{PAPER.journal}</i>, {PAPER.volume}({PAPER.number}). {PAPER.license}.
          </p>
          <ul className="site-footer__notes">
            <li>Category shares (Figures 6 &amp; 8) are exact; each series sums to 100%.</li>
            <li>
              Sub-category (Figures 5 &amp; 7) and virtualization radar (Figure 11) values were read
              from the charts and are approximate.
            </li>
            <li>
              The defense matrix lists current best practice mapped to the paper’s categories; the
              controls themselves are not from the paper.
            </li>
            <li>
              The R1–R4 requirements quote the paper (p.16); their interpretation, the system and all
              measurements are this project’s own. Containers stand in for VMs (see Requirements).
            </li>
          </ul>
        </section>
      </div>
    </footer>
  )
}
