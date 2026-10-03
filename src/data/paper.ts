// Bibliographic record for the source paper, mirrored from docs/paper-content.md.

export interface Citation {
  authors: readonly string[]
  year: number
  title: string
  journal: string
  volume: number
  number: number
  license: string
  /** In-text form, e.g. for figure captions. */
  short: string
}

export const PAPER: Citation = {
  authors: [
    'Gonzalez, N.',
    'Miers, C.',
    'Redígolo, F.',
    'Simplício, M.',
    'Carvalho, T.',
    'Näslund, M.',
    'Pourzandi, M.',
  ],
  year: 2012,
  title:
    'A quantitative analysis of current security concerns and solutions for cloud computing',
  journal: 'Journal of Cloud Computing: Advances, Systems and Applications',
  volume: 1,
  number: 11,
  license: 'Open Access (CC BY 2.0)',
  short: 'Gonzalez et al. (2012)',
}

/** APA-style author list: "A, B, … & Z". */
export function formatAuthors(authors: readonly string[]): string {
  if (authors.length <= 1) return authors.join('')
  return `${authors.slice(0, -1).join(', ')}, & ${authors[authors.length - 1]}`
}
