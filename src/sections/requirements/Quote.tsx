import { PAPER_QUOTE, REQUIREMENTS } from '../../data/requirements'
import './Quote.css'

/** The p.16 passage, verbatim, with each requirement's phrase marked R1-R4. */
export function QuoteWithRequirements() {
  // Split the quote around the four phrases, in the order they appear.
  const parts: { text: string; req?: string }[] = []
  let rest = PAPER_QUOTE
  for (const r of REQUIREMENTS) {
    const at = rest.indexOf(r.phrase)
    if (at < 0) continue
    parts.push({ text: rest.slice(0, at) })
    parts.push({ text: r.phrase, req: r.id })
    rest = rest.slice(at + r.phrase.length)
  }
  parts.push({ text: rest })

  return (
    <blockquote className="paper-quote">
      <p>
        “
        {parts.map((p, i) =>
          p.req ? (
            <mark key={i} className="paper-quote__mark">
              {p.text}
              <sup>{p.req}</sup>
            </mark>
          ) : (
            <span key={i}>{p.text}</span>
          ),
        )}
        ”
      </p>
      <footer>Gonzalez et al. (2012), “Considerations and future work”, p.16</footer>
    </blockquote>
  )
}
