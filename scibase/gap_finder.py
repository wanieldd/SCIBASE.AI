"""Research gap finder.

Scans a corpus of papers and identifies under-studied topic intersections,
frequently cited unresolved questions, and generates a "research
opportunities" feed personalized for a user's interests and project history.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MIN_POPULARITY = 3  # a topic must appear this many times to count as "active"
MIN_INTEREST_OVERLAP = 1  # opportunities must share this many user interests


@dataclass
class Paper:
    """A paper in the scanned corpus.

    Parameters
    ----------
    id:
        Stable paper identifier.
    title:
        Paper title.
    abstract:
        Paper abstract.
    topics:
        Topics covered by the paper.
    citations:
        Number of times the paper has been cited (published + in-progress).
    open_questions:
        Explicit unresolved questions stated in the paper (e.g. limitations
        sections that suggest open directions).
    """

    id: str
    title: str
    abstract: str = ""
    topics: list[str] = field(default_factory=list)
    citations: int = 0
    open_questions: list[str] = field(default_factory=list)


@dataclass
class ResearchOpportunity:
    """A suggested research direction derived from corpus gaps.

    Parameters
    ----------
    topics:
        The under-studied topic combination.
    popularity:
        How often each member topic appears in the corpus.
    combination_count:
        How many papers cover the full combination.
    rationale:
        Human-readable justification for the suggestion.
    relevance:
        Number of user interests / project topics the opportunity overlaps.
    """

    topics: frozenset[str]
    popularity: dict[str, int]
    combination_count: int
    rationale: str
    relevance: int = 0

    @property
    def score(self) -> float:
        """Recommendation score: active topics, low replication, high relevance."""
        activity = sum(self.popularity.values())
        return round((activity * (1 + self.relevance)) / (1 + self.combination_count), 2)


class GapFinder:
    """Identifies research gaps across a corpus of :class:`Paper` objects."""

    def __init__(self, papers: list[Paper] | None = None) -> None:
        self.papers: list[Paper] = papers or []

    def add(self, paper: Paper) -> None:
        """Add a paper to the corpus."""
        self.papers.append(paper)

    def add_papers(self, papers: list[Paper]) -> None:
        """Add several papers to the corpus."""
        self.papers.extend(papers)

    # Public API ---------------------------------------------------------------

    def topic_popularity(self) -> dict[str, int]:
        """Count how many papers cover each topic."""
        counts: dict[str, int] = {}
        for paper in self.papers:
            for topic in paper.topics:
                counts[topic] = counts.get(topic, 0) + 1
        return counts

    def under_studied_intersections(self, size: int = 2) -> list[ResearchOpportunity]:
        """Find topic combinations with high activity but low replication.

        A combination is considered a gap when every member topic is
        individually active (appears at least :data:`MIN_POPULARITY` times)
        but the combination itself is covered by very few papers. Pairs where
        every paper already covers all members are excluded.

        Parameters
        ----------
        size:
            Number of topics per combination.

        Returns
        -------
        list[ResearchOpportunity]
            Opportunities sorted by recommendation score (descending).
        """
        popularity = self.topic_popularity()
        active = sorted(t for t, n in popularity.items() if n >= MIN_POPULARITY)

        from itertools import combinations

        opportunities: list[ResearchOpportunity] = []
        for combo in combinations(active, size):
            combo_set = frozenset(combo)
            covering = [
                paper
                for paper in self.papers
                if combo_set.issubset(set(paper.topics))
            ]
            combo_popularity = {t: popularity[t] for t in combo}
            if not covering:
                rationale = (
                    f"Topics {', '.join(combo)} are individually active but never co-occur in the corpus."
                )
            else:
                combo_count = len(covering)
                fully_covered = sum(1 for p in covering if set(p.topics) <= combo_set)
                if fully_covered == combo_count:
                    continue  # every paper on these topics already covers the full intersection
                rationale = (
                    f"Topics {', '.join(combo)} co-occur in only {combo_count} paper(s) "
                    "despite high individual activity."
                )
            opportunities.append(
                ResearchOpportunity(
                    topics=combo_set,
                    popularity=combo_popularity,
                    combination_count=len(covering),
                    rationale=rationale,
                )
            )

        opportunities.sort(key=lambda o: o.score, reverse=True)
        return opportunities

    def unresolved_questions(self, min_citations: int = 5) -> list[tuple[str, int, int]]:
        """Return frequently cited unresolved questions.

        Questions are extracted from each paper's ``open_questions`` list and
        aggregated. Only questions appearing in papers with at least
        ``min_citations`` citations are returned.

        Parameters
        ----------
        min_citations:
            Minimum citation count for a paper's questions to be included.

        Returns
        -------
        list[tuple[str, int, int]]
            ``(question, paper_count, total_citations)`` sorted by total
            citations (descending).
        """
        questions: dict[str, list[int]] = {}
        for paper in self.papers:
            if paper.citations < min_citations:
                continue
            for question in paper.open_questions:
                key = question.strip().rstrip("?")
                if not key:
                    continue
                questions.setdefault(key, []).append(paper.citations)

        result = [
            (question, len(cites), sum(cites))
            for question, cites in questions.items()
        ]
        result.sort(key=lambda item: item[2], reverse=True)
        return result

    def research_opportunities_feed(
        self,
        interests: list[str],
        project_history: list[str] | None = None,
        size: int = 2,
    ) -> list[ResearchOpportunity]:
        """Generate a personalized "research opportunities" feed.

        Under-studied intersections are ranked by overlap with the user's
        interests and project history. An opportunity must overlap at least
        :data:`MIN_INTEREST_OVERLAP` interest/project topic to be included.

        Parameters
        ----------
        interests:
            Topics the user is interested in.
        project_history:
            Topics from the user's past projects.
        size:
            Number of topics per intersection.

        Returns
        -------
        list[ResearchOpportunity]
            Personalized opportunities sorted by recommendation score.
        """
        context = set(interests) | set(project_history or [])
        opportunities = self.under_studied_intersections(size=size)

        feed: list[ResearchOpportunity] = []
        for opportunity in opportunities:
            relevance = len(opportunity.topics & context)
            if relevance < MIN_INTEREST_OVERLAP:
                continue
            feed.append(
                ResearchOpportunity(
                    topics=opportunity.topics,
                    popularity=opportunity.popularity,
                    combination_count=opportunity.combination_count,
                    rationale=opportunity.rationale,
                    relevance=relevance,
                )
            )

        feed.sort(key=lambda o: o.score, reverse=True)
        return feed


def extract_questions(text: str) -> list[str]:
    """Extract explicit unresolved-question sentences from a text.

    Looks for sentences containing interrogative phrasing typical of
    limitations sections ("remains unclear", "future work", "open question",
    etc.) or ending with a question mark.

    Parameters
    ----------
    text:
        Text to scan (e.g. a paper's limitations section).

    Returns
    -------
    list[str]
        Extracted question sentences.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    found: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if "?" in sentence or any(
            marker in lowered
            for marker in ("remains unclear", "open question", "future work", "not well understood", "requires further")
        ):
            found.append(sentence.strip())
    return found