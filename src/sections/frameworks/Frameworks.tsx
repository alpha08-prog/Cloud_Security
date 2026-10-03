import { FRAMEWORKS, type FrameworkOrg } from '../../data/frameworks'
import './Frameworks.css'

const ORGS: { org: FrameworkOrg; name: string }[] = [
  { org: 'CSA', name: 'Cloud Security Alliance' },
  { org: 'ENISA', name: 'European Union Agency for Cybersecurity' },
  { org: 'NIST', name: 'National Institute of Standards and Technology' },
]

export function Frameworks() {
  return (
    <div className="frameworks">
      {ORGS.map(({ org, name }) => (
        <section key={org} className="frameworks__group" aria-labelledby={`org-${org}`}>
          <h3 className="frameworks__org" id={`org-${org}`}>
            {org} <span className="frameworks__org-name">{name}</span>
          </h3>
          <div className="frameworks__grid">
            {FRAMEWORKS.filter((f) => f.org === org).map((f) => (
              <article key={f.id} className="card framework">
                <h4 className="framework__name">{f.name}</h4>
                <ul className="framework__points">
                  {f.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
                {f.lists?.map((list) => (
                  <div key={list.label} className="framework__list">
                    <p className="eyebrow">
                      {list.label} ({list.items.length})
                    </p>
                    <ul className="framework__chips">
                      {list.items.map((item) => (
                        <li key={item} className="badge">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </article>
            ))}
          </div>
        </section>
      ))}
      <p className="figure-caption">
        <strong>Source:</strong> summarised from Gonzalez et al. (2012), Tables 1 &amp; 2.
      </p>
    </div>
  )
}
