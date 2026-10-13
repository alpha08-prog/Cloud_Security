"""Classify one title + abstract with the frozen keyword rules (docs/replication.md §3).

Output per work: whether it is in scope (relevance gate), its type (survey / solution /
concern), the Figure-5 sub-categories it raises as concerns and offers solutions for
(rule B, scoped), and the Figure-11 virtualization sub-issues the same way.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from . import lexicon, taxonomy

# Also splits "end.Next" (OpenAlex abstracts often lose the space after a full stop).
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9\"'(\[])|(?<=[a-z0-9)][.!?])(?=[A-Z][a-z])")


_LEAD = r"(?<![\w])"


def compile_term(term: str) -> tuple[str, bool]:
    """-> (regex, case_sensitive). See lexicon.py for the syntax."""
    if term.startswith("re:"):
        return f"(?:{term[3:]})", False
    letters = re.sub(r"[^A-Za-z]", "", term)
    case_sensitive = bool(letters) and letters.isupper() and len(letters) > 1
    words = re.split(r"\s+", term.strip())
    parts = []
    for i, word in enumerate(words):
        stem = word.endswith("*")
        w = word.rstrip("*")
        pieces = [re.escape(p) for p in w.split("-")]
        body = r"[\s\-]?".join(pieces)
        if stem:
            body += r"\w*"
        elif i == len(words) - 1 and not case_sensitive and w[-1:].isalpha():
            body += r"(?:s|es)?"
        parts.append(body)
    pattern = r"[\s\-]+".join(parts)
    lead = _LEAD if re.match(r"\w", words[0]) else ""
    tail = r"(?![\w])" if not words[-1].endswith("*") and re.search(r"\w$", words[-1].rstrip("*")) else ""
    if words[-1].endswith("*"):
        tail = ""
    return f"{lead}(?:{pattern}){tail}", case_sensitive


class TermSet:
    """A list of lexicon terms compiled into (at most) two alternation regexes."""

    def __init__(self, terms: list[str]):
        groups: dict[bool, tuple[list[str], list[str]]] = {False: ([], []), True: ([], [])}
        for t in terms:
            pattern, sensitive = compile_term(t)
            led, other = groups[sensitive]
            if pattern.startswith(_LEAD):
                led.append(pattern[len(_LEAD):])
            else:
                other.append(pattern)

        def build(led: list[str], other: list[str], flags: int) -> re.Pattern | None:
            # One shared word-start lookbehind instead of one per alternative: same matches, and
            # positions inside a word are rejected before the alternation is tried (much faster).
            parts = ([f"{_LEAD}(?:{'|'.join(led)})"] if led else []) + other
            return re.compile("|".join(parts), flags) if parts else None

        self._ci = build(*groups[False], re.IGNORECASE)
        self._cs = build(*groups[True], 0)

    def _regexes(self):
        return [r for r in (self._ci, self._cs) if r is not None]

    def search(self, text: str) -> bool:
        return any(r.search(text) for r in self._regexes())

    def count(self, text: str) -> int:
        return sum(len(r.findall(text)) for r in self._regexes())

    def mask(self, text: str) -> str:
        for r in self._regexes():
            text = r.sub(lambda m: " " * len(m.group(0)), text)
        return text


@dataclass
class _Rule:
    terms: TermSet
    virt: TermSet | None
    net: TermSet | None
    threat: TermSet | None
    exclude: TermSet | None


def _rule(spec: dict) -> _Rule:
    return _Rule(terms=TermSet(spec.get("terms", [])),
                 virt=TermSet(spec["virt"]) if spec.get("virt") else None,
                 net=TermSet(spec["net"]) if spec.get("net") else None,
                 threat=TermSet(spec["threat"]) if spec.get("threat") else None,
                 exclude=TermSet(spec["exclude"]) if spec.get("exclude") else None)


GLOBAL_EXCLUDE = TermSet(lexicon.GLOBAL_EXCLUDE)
VIRT_CONTEXT = TermSet(lexicon.VIRT_CONTEXT)
NET_CONTEXT = TermSet(lexicon.NET_CONTEXT)
THREAT_CONTEXT = TermSet(lexicon.THREAT_CONTEXT)
CLOUD = TermSet(lexicon.CLOUD_TERMS)
SECURITY = TermSet(lexicon.SECURITY_TERMS)
SUB_RULES = {name: _rule(spec) for name, spec in lexicon.SUBCATEGORIES.items()}
AXIS_RULES = {name: _rule(spec) for name, spec in lexicon.AXES.items()}
NON_CLASSIC = TermSet(lexicon.NON_CLASSIC)
SURVEY_TITLE = TermSet(lexicon.SURVEY_TITLE)
SURVEY_LEAD = TermSet(lexicon.SURVEY_LEAD)
SUBJECT = TermSet(lexicon.SUBJECT_CUES)
VERB = TermSet(lexicon.CONTRIBUTION_VERBS)
ARTIFACT = TermSet(lexicon.ARTIFACT_NOUNS)
PASSIVE = TermSet(lexicon.PASSIVE_CONTRIBUTION)
NOT_OURS = TermSet(lexicon.NOT_OURS)
ATTACK = TermSet(lexicon.ATTACK_CUES)
DEFENSIVE = TermSet(lexicon.DEFENSIVE_CUES)


def sentences(title: str, abstract: str) -> list[str]:
    """Title first (sentence 0), then the abstract's sentences."""
    return [title.strip()] + [s for s in SENTENCE_SPLIT.split(abstract.strip()) if s]


def _hits(rule: _Rule, sent: list[str], whole: str) -> list[int]:
    # Masking only removes matches, so no match in the whole text means no hit anywhere.
    if not any(t.search(whole) for t in (rule.terms, rule.virt, rule.net, rule.threat) if t):
        return []
    out = []
    for i, s in enumerate(sent):
        text = rule.exclude.mask(s) if rule.exclude else s
        if rule.terms.search(text):
            out.append(i)
        elif rule.virt and rule.virt.search(text) and VIRT_CONTEXT.search(text):
            out.append(i)
        elif rule.net and rule.net.search(text) and NET_CONTEXT.search(text):
            out.append(i)
        elif rule.threat and rule.threat.search(text) and THREAT_CONTEXT.search(text):
            out.append(i)
    return out


def is_contribution(s: str) -> bool:
    s = NOT_OURS.mask(s)
    if not (PASSIVE.search(s) or (SUBJECT.search(s) and VERB.search(s) and ARTIFACT.search(s))):
        return False
    # Presenting an attack is not a solution unless the sentence is also defensive.
    if ATTACK.search(s) and not DEFENSIVE.search(s):
        return False
    return True


@dataclass
class Result:
    id: str
    in_scope: bool
    gate_cloud: bool
    gate_security: bool
    gate_joint: bool
    kind: str                         # survey | solution | concern
    concern: list[str] = field(default_factory=list)      # Figure-5 sub-categories
    solution: list[str] = field(default_factory=list)
    axes_concern: list[str] = field(default_factory=list)  # Figure-11 sub-issues
    axes_solution: list[str] = field(default_factory=list)
    classic_axes: list[str] = field(default_factory=list)  # axes with a hit in a sentence without non-classic terms
    classic_axes_solution: list[str] = field(default_factory=list)  # the same, inside the solution window (RB3)
    broadcast_solution: list[str] = field(default_factory=list)  # rule A (RB2)

    def categories(self, which: str = "concern") -> list[str]:
        subs = self.concern if which == "concern" else self.solution
        return sorted({taxonomy.category_of(s) for s in subs})

    def dump(self) -> dict:
        return asdict(self)


def classify(work_id: str, title: str, abstract: str) -> Result:
    raw = sentences(title, abstract)
    sent = [GLOBAL_EXCLUDE.mask(s) for s in raw]
    abstract_text = " ".join(sent[1:])

    gate_cloud = CLOUD.search(sent[0]) or CLOUD.count(abstract_text) >= 2
    gate_security = SECURITY.search(sent[0]) or SECURITY.count(abstract_text) >= 2
    # ... and the two must meet: one sentence (the title counts) names both.
    gate_joint = any(CLOUD.search(s) and SECURITY.search(s) for s in sent)

    whole = "\n".join(sent)
    sub_hits = {name: _hits(rule, sent, whole) for name, rule in SUB_RULES.items()}
    axis_hits = {name: _hits(rule, sent, whole) for name, rule in AXIS_RULES.items()}
    for axis, idx in axis_hits.items():  # the paper's fold: Figure-11 sub-issues -> Figure-5 rows
        if idx:
            row = taxonomy.FOLD[axis]
            sub_hits[row] = sorted(set(sub_hits.get(row, [])) | set(idx))
    concern = sorted(s for s, idx in sub_hits.items() if idx)
    axes = sorted(a for a, idx in axis_hits.items() if idx)
    classic_hits = {a: [i for i in idx if not NON_CLASSIC.search(sent[i])] for a, idx in axis_hits.items()}
    classic = sorted(a for a, idx in classic_hits.items() if idx)

    lead = " ".join(sent[1:3])
    if SURVEY_TITLE.search(sent[0]) or SURVEY_LEAD.search(lead):
        kind = "survey"
    elif any(is_contribution(s) for s in sent[1:]):
        kind = "solution"
    else:
        kind = "concern"

    solution: list[str] = []
    axes_solution: list[str] = []
    classic_solution: list[str] = []
    if kind == "solution":
        first = next(i for i, s in enumerate(sent) if i > 0 and is_contribution(s))
        scope = {0, *range(first, len(sent))}  # the title + from the first contribution sentence on
        # The window is decided once, from the Figure-5 hits, and the Figure-11 sub-issues follow it,
        # so a sub-issue named only in the problem statement never becomes a solution on its own.
        if not any(scope.intersection(idx) for idx in sub_hits.values()):
            scope = set(range(len(sent)))  # nothing in scope: fall back to every hit
        solution = sorted(k for k, idx in sub_hits.items() if scope.intersection(idx))
        axes_solution = sorted(k for k, idx in axis_hits.items() if scope.intersection(idx))
        classic_solution = sorted(k for k, idx in classic_hits.items() if scope.intersection(idx))
    broadcast = list(concern) if kind == "solution" else []

    return Result(id=work_id, in_scope=bool(gate_cloud and gate_security and gate_joint and concern),
                  gate_cloud=bool(gate_cloud), gate_security=bool(gate_security), gate_joint=gate_joint, kind=kind,
                  concern=concern, solution=solution, axes_concern=axes, axes_solution=axes_solution,
                  classic_axes=classic, classic_axes_solution=classic_solution, broadcast_solution=broadcast)


# ---------------------------------------------------------------------------- CVE supplement (§6)
NVD_CONTEXT = TermSet(lexicon.NVD_VIRT_CONTEXT)
NVD_EXCLUDE = TermSet(lexicon.NVD_EXCLUDE)
NVD_RULES = {axis: TermSet(terms) for axis, terms in lexicon.NVD_AXES.items()}


def classify_cve(description: str) -> list[str]:
    """The CVE axes a description matches. Every axis needs a virtualization context (the
    layer axis's own terms are one); VM identification has no defensible proxy and is never set."""
    text = NVD_EXCLUDE.mask(description)
    if not NVD_CONTEXT.search(text):
        return []
    return sorted(axis for axis, rule in NVD_RULES.items() if rule.search(text))
