"""
Similarity and citation-coverage analysis
=========================================
Word-shingle overlap between a document and a corpus **you supply** — the
project's own sections, uploaded references, and pasted sources. That is the
honest boundary of this module: it can prove a passage matches something in
your corpus, and it can show which claims carry no citation. It cannot tell
you whether a passage exists somewhere on the web, because it has no licensed
index to compare against. :data:`SCOPE_NOTE` is the wording the UI must show
next to any percentage produced here.

Two numbers are reported and they answer different questions:

* ``overall_similarity`` — share of the document's shingles found in the
  corpus. High values mean copying *from your corpus*.
* ``citation_coverage`` — share of citation-worthy sentences that carry a
  reference marker. Low values mean unsupported claims, which is what an
  examiner actually reads for.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

SCOPE_NOTE = (
    "Similarity is measured against this workspace's corpus and the references "
    "you supplied — not against the web. It is not a plagiarism verdict."
)

DEFAULT_SHINGLE = 5
MIN_PASSAGE_SHINGLES = 2

WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# (Author, 2020) / (Author et al., 2020) / [12] / [12, 13] / ¹²
CITATION_RE = re.compile(
    r"\([^()]*\b(?:19|20)\d{2}[a-z]?\)|\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]|\bibid\b",
    re.IGNORECASE,
)
# Sentences that assert something checkable and therefore want a source.
CLAIM_CUES = (
    "show", "shows", "shown", "demonstrate", "demonstrates", "demonstrated",
    "found", "finds", "report", "reports", "reported", "reveal", "reveals",
    "suggest", "suggests", "indicate", "indicates", "according", "evidence",
    "study", "studies", "research", "literature", "prior", "previous",
    "estimated", "association", "correlation", "significant",
)
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%|\b\d{2,}\b")


def words(text: str) -> List[str]:
    return [w.lower() for w in WORD_RE.findall(text or "")]


def shingles(text: str, size: int = DEFAULT_SHINGLE) -> List[Tuple[str, int]]:
    """``(shingle, index of its first word)`` pairs, in document order."""
    tokens = words(text)
    if len(tokens) < size:
        return []
    return [
        (" ".join(tokens[i: i + size]), i) for i in range(len(tokens) - size + 1)
    ]


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    text: str


@dataclass(frozen=True)
class Passage:
    """A run of consecutive matching shingles, quoted from the document."""

    source_id: str
    source_title: str
    start_word: int
    end_word: int
    text: str

    @property
    def word_count(self) -> int:
        return self.end_word - self.start_word


@dataclass
class SourceMatch:
    source_id: str
    source_title: str
    matched_shingles: int
    similarity: float
    passages: List[Passage] = field(default_factory=list)


@dataclass
class SimilarityReport:
    overall_similarity: float
    total_shingles: int
    matched_shingles: int
    matches: List[SourceMatch] = field(default_factory=list)
    scope_note: str = SCOPE_NOTE

    @property
    def top_source(self) -> Optional[SourceMatch]:
        return self.matches[0] if self.matches else None

    def passages(self, limit: int = 25) -> List[Passage]:
        """Longest matching passages across every source."""
        everything = [p for m in self.matches for p in m.passages]
        everything.sort(key=lambda p: p.word_count, reverse=True)
        return everything[:limit]


def _passages_from_hits(
    tokens: List[str],
    hits: Sequence[int],
    size: int,
    source: Source,
) -> List[Passage]:
    """Merge consecutive shingle hits into readable passages."""
    passages: List[Passage] = []
    run_start: Optional[int] = None
    previous: Optional[int] = None
    run_length = 0

    def close(last: int) -> None:
        if run_start is None or run_length < MIN_PASSAGE_SHINGLES:
            return
        end = last + size
        passages.append(
            Passage(
                source_id=source.id,
                source_title=source.title,
                start_word=run_start,
                end_word=end,
                text=" ".join(tokens[run_start:end]),
            )
        )

    for index in hits:
        if previous is not None and index == previous + 1:
            run_length += 1
        else:
            if previous is not None:
                close(previous)
            run_start, run_length = index, 1
        previous = index
    if previous is not None:
        close(previous)
    return passages


def compare(
    text: str,
    sources: Sequence[Source],
    size: int = DEFAULT_SHINGLE,
) -> SimilarityReport:
    """Compare ``text`` against every source, attributing matches per source."""
    doc_shingles = shingles(text, size)
    if not doc_shingles or not sources:
        return SimilarityReport(0.0, len(doc_shingles), 0, [])

    tokens = words(text)
    unique_total = len({s for s, _ in doc_shingles})
    matched_overall: set = set()
    matches: List[SourceMatch] = []

    for source in sources:
        source_set = {s for s, _ in shingles(source.text, size)}
        if not source_set:
            continue
        hits: List[int] = []
        hit_shingles: set = set()
        for shingle, index in doc_shingles:
            if shingle in source_set:
                hits.append(index)
                hit_shingles.add(shingle)
        if not hits:
            continue
        matched_overall |= hit_shingles
        matches.append(
            SourceMatch(
                source_id=source.id,
                source_title=source.title,
                matched_shingles=len(hit_shingles),
                similarity=round(len(hit_shingles) / unique_total * 100, 2),
                passages=_passages_from_hits(tokens, hits, size, source),
            )
        )

    matches.sort(key=lambda m: m.similarity, reverse=True)
    return SimilarityReport(
        overall_similarity=round(len(matched_overall) / unique_total * 100, 2),
        total_shingles=unique_total,
        matched_shingles=len(matched_overall),
        matches=matches,
    )


def heatmap(
    text: str,
    sources: Sequence[Source],
    segments: int = 12,
    size: int = DEFAULT_SHINGLE,
) -> Tuple[List[str], List[str], List[List[float]]]:
    """``(segment labels, source labels, matrix)`` for a plotly heatmap.

    The document is cut into ``segments`` equal slices so a reader can see
    *where* the overlap sits rather than one aggregate number.
    """
    tokens = words(text)
    usable = [s for s in sources if shingles(s.text, size)]
    if not tokens or not usable:
        return [], [], []
    segments = max(1, min(segments, max(1, len(tokens) // size)))
    step = max(size, len(tokens) // segments)

    slices = [tokens[i: i + step] for i in range(0, len(tokens), step)][:segments]
    labels = [f"{i * step + 1}–{i * step + len(chunk)}" for i, chunk in enumerate(slices)]
    source_labels = [s.title for s in usable]
    source_sets = [{sh for sh, _ in shingles(s.text, size)} for s in usable]

    matrix: List[List[float]] = []
    for source_set in source_sets:
        row = []
        for chunk in slices:
            chunk_shingles = {
                " ".join(chunk[i: i + size]) for i in range(len(chunk) - size + 1)
            }
            row.append(
                round(len(chunk_shingles & source_set) / len(chunk_shingles) * 100, 2)
                if chunk_shingles
                else 0.0
            )
        matrix.append(row)
    return labels, source_labels, matrix


# ═══════════════════════════════════════════════════════════════════════
# Citation coverage
# ═══════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Sentence:
    text: str
    index: int
    needs_citation: bool
    has_citation: bool


@dataclass
class CitationReport:
    coverage: float
    claims: int
    cited_claims: int
    uncited: List[Sentence] = field(default_factory=list)
    markers: int = 0

    @property
    def verdict(self) -> str:
        if not self.claims:
            return "No citation-worthy claims detected."
        if self.coverage >= 90:
            return "Claims are well supported."
        if self.coverage >= 60:
            return "Some claims still need a source."
        return "Most claims are unsupported."


def sentences(text: str) -> List[str]:
    return [s.strip() for s in SENTENCE_RE.split(text or "") if s.strip()]


def needs_citation(sentence: str) -> bool:
    """True for sentences that assert a checkable fact."""
    lowered = sentence.lower()
    if any(f" {cue} " in f" {lowered} " for cue in CLAIM_CUES):
        return True
    return bool(NUMBER_RE.search(sentence))


def citation_coverage(text: str) -> CitationReport:
    """Share of citation-worthy sentences that carry a reference marker."""
    analysed: List[Sentence] = []
    markers = 0
    for index, raw in enumerate(sentences(text)):
        cited = bool(CITATION_RE.search(raw))
        markers += len(CITATION_RE.findall(raw))
        analysed.append(Sentence(raw, index, needs_citation(raw), cited))

    claims = [s for s in analysed if s.needs_citation]
    cited = [s for s in claims if s.has_citation]
    coverage = round(len(cited) / len(claims) * 100, 2) if claims else 100.0
    return CitationReport(
        coverage=coverage,
        claims=len(claims),
        cited_claims=len(cited),
        uncited=[s for s in claims if not s.has_citation],
        markers=markers,
    )


def repeated_phrases(text: str, size: int = 8, min_count: int = 2) -> List[Tuple[str, int]]:
    """Phrases the document repeats verbatim — usually padding or a paste."""
    counts = Counter(shingle for shingle, _ in shingles(text, size))
    return sorted(
        ((phrase, n) for phrase, n in counts.items() if n >= min_count),
        key=lambda item: item[1],
        reverse=True,
    )


def summarise(text: str, sources: Sequence[Source]) -> Dict[str, object]:
    """Everything a UI panel or an emailed report needs, in one call."""
    similarity = compare(text, sources)
    citations = citation_coverage(text)
    return {
        "similarity": similarity.overall_similarity,
        "matched_shingles": similarity.matched_shingles,
        "total_shingles": similarity.total_shingles,
        "top_source": similarity.top_source.source_title if similarity.top_source else None,
        "citation_coverage": citations.coverage,
        "uncited_claims": len(citations.uncited),
        "scope_note": SCOPE_NOTE,
    }
