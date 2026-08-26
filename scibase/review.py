"""Auto peer review report generation.

Analyzes a manuscript and produces structured, category-based review
suggestions covering clarity and coherence, statistical and methodological
red flags, missing citations, and claims-vs-evidence alignment. Templates are
adaptable per research domain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

SEVERITY_WEIGHTS = {"error": 10, "warning": 4, "info": 1}

DEFAULT_DOMAIN_TEMPLATES: dict[str, dict[str, str]] = {
    "molecular-biology": {
        "name": "Molecular Biology",
        "intro": "Review guided by molecular biology reporting standards.",
        "checks": "Verify cell lines, replicate counts, and reagent lot numbers.",
    },
    "quantum-physics": {
        "name": "Quantum Physics",
        "intro": "Review guided by quantum physics reporting standards.",
        "checks": "Verify gate fidelities, decoherence times, and error bars.",
    },
    "clinical-trials": {
        "name": "Clinical Trials",
        "intro": "Review guided by clinical trial reporting standards.",
        "checks": "Verify randomization, blinding, and adverse-event reporting.",
    },
}


class ReviewCategory(str, Enum):
    """Categories of review feedback produced by :func:`generate_peer_review`."""

    CLARITY = "clarity"
    STATISTICAL = "statistical"
    METHODOLOGY = "methodology"
    CITATION = "citations"
    CLAIMS = "claims"
    SCOPE = "scope"


@dataclass
class Manuscript:
    """The document being reviewed.

    Parameters
    ----------
    title:
        Manuscript title.
    abstract:
        Abstract text (subject to clarity/claims checks).
    body:
        Main manuscript text (subject to statistical/methodological checks).
    claims:
        Claims stated by the authors as ``(assertion, evidence)`` pairs.
        ``evidence`` may be ``None`` when the claim is unsupported.
    citations:
        References cited in the manuscript.
    domain:
        Optional domain key (e.g. ``"clinical-trials"``) used to select an
        adaptive review template. Unknown domains fall back to a generic
        template.
    """

    title: str
    abstract: str
    body: str = ""
    claims: list[tuple[str, str | None]] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    domain: str | None = None


@dataclass
class ReviewIssue:
    """A single structured review suggestion."""

    category: ReviewCategory
    severity: str
    location: str
    message: str
    suggestion: str

    @property
    def weight(self) -> int:
        """Severity weight used when scoring the report."""
        return SEVERITY_WEIGHTS.get(self.severity, 0)


@dataclass
class ReviewReport:
    """Structured output of a peer review pass over a manuscript."""

    title: str
    domain: str | None
    issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def score(self) -> int:
        """Peer review score on a 0-100 scale (higher is better)."""
        if not self.issues:
            return 100
        deduction = sum(issue.weight for issue in self.issues)
        return max(0, min(100, 100 - deduction))


# Heuristic rules -----------------------------------------------------------------


def _find_clarity_issues(manuscript: Manuscript) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    text = f"{manuscript.abstract}\n{manuscript.body}"

    if len(text.split()) < 40:
        issues.append(
            ReviewIssue(
                category=ReviewCategory.CLARITY,
                severity="warning",
                location="manuscript",
                message="The manuscript body is very short and may lack sufficient detail.",
                suggestion="Expand the manuscript with the methods, results, and discussion sections.",
            )
        )

    jargon = re.findall(r"\b(?:etc\.|very|extremely|significantly|novel|robust)\b", text, re.IGNORECASE)
    if jargon:
        issues.append(
            ReviewIssue(
                category=ReviewCategory.CLARITY,
                severity="info",
                location="manuscript",
                message=(
                    "Vague or overused wording detected "
                    f"(e.g. {', '.join(dict.fromkeys(j.lower() for j in jargon))})."
                ),
                suggestion="Replace vague qualifiers with concrete measurements or precise language.",
            )
        )

    sentences = re.split(r"[.!?]\s+", text)
    long = [s for s in sentences if len(s.split()) > 60]
    if long:
        issues.append(
            ReviewIssue(
                category=ReviewCategory.CLARITY,
                severity="warning",
                location="manuscript",
                message=f"{len(long)} sentence(s) exceed 60 words and harm readability.",
                suggestion="Split long sentences to improve readability and coherence.",
            )
        )

    return issues


def _find_statistical_issues(manuscript: Manuscript) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    text = f"{manuscript.abstract}\n{manuscript.body}".lower()

    if "p-value" in text or "p value" in text or "p<" in text or "p <" in text:
        if not re.search(r"p\s*[<>=]\s*0?\.?\d", text):
            issues.append(
                ReviewIssue(
                    category=ReviewCategory.STATISTICAL,
                    severity="error",
                    location="abstract/body",
                    message="A p-value is mentioned without a reported numerical value.",
                    suggestion="Report the exact p-value (e.g. p = 0.023) alongside the test used.",
                )
            )

    if re.search(r"\bsample size\b", text):
        if not re.search(r"\bsample size\b[^\n]{0,120}\d", text):
            issues.append(
                ReviewIssue(
                    category=ReviewCategory.STATISTICAL,
                    severity="warning",
                    location="methods",
                    message="Sample size is mentioned without a reported number.",
                    suggestion="State the exact sample size and the power analysis that justified it.",
                )
            )

    if re.search(r"\bcorrelat", text) and not re.search(r"\br\s*[=]\s*-?\d", text):
        issues.append(
            ReviewIssue(
                category=ReviewCategory.STATISTICAL,
                severity="warning",
                location="results",
                message="A correlation is claimed without reporting the coefficient.",
                suggestion="Report the correlation coefficient (r) and its confidence interval.",
            )
        )

    return issues


def _find_methodological_issues(manuscript: Manuscript) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    text = f"{manuscript.abstract}\n{manuscript.body}".lower()

    if re.search(r"\bsurvey\b", text) and not re.search(r"\bresponse rate\b", text):
        issues.append(
            ReviewIssue(
                category=ReviewCategory.METHODOLOGY,
                severity="warning",
                location="methods",
                message="A survey-based study is reported without a response rate.",
                suggestion="Report the response rate and sampling strategy.",
            )
        )

    return issues


def _find_citation_issues(manuscript: Manuscript) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    text = f"{manuscript.abstract}\n{manuscript.body}"

    if not manuscript.citations:
        issues.append(
            ReviewIssue(
                category=ReviewCategory.CITATION,
                severity="error",
                location="manuscript",
                message="No citations were provided for the manuscript.",
                suggestion="Add citations supporting key claims and prior work.",
            )
        )

    # A claim is expected to reference prior literature; if the body uses
    # "shown to" / "previous work" but cites nothing, flag scope alignment.
    if manuscript.citations and re.search(r"\bshown to\b|\bprevious work\b|\bas reported\b", text) and len(manuscript.citations) < 2:
        issues.append(
            ReviewIssue(
                category=ReviewCategory.CITATION,
                severity="warning",
                location="introduction",
                message="The manuscript references prior work but cites very few sources.",
                suggestion="Add citations for each reference to previous work.",
            )
        )

    return issues


def _find_claims_issues(manuscript: Manuscript) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []

    for idx, (claim, evidence) in enumerate(manuscript.claims, start=1):
        location = f"claim #{idx}"
        if evidence is None or not evidence.strip():
            issues.append(
                ReviewIssue(
                    category=ReviewCategory.CLAIMS,
                    severity="error",
                    location=location,
                    message=f"Claim is not supported by evidence: {claim!r}",
                    suggestion="Provide supporting data, analysis, or a citation for this claim.",
                )
            )
        elif len(evidence.split()) < 3:
            issues.append(
                ReviewIssue(
                    category=ReviewCategory.CLAIMS,
                    severity="warning",
                    location=location,
                    message=f"Evidence for claim is too thin: {claim!r}",
                    suggestion="Strengthen the evidence with quantitative results or citations.",
                )
            )

    return issues


def _resolve_domain(domain: str | None) -> dict[str, str] | None:
    if domain is None:
        return None
    return DEFAULT_DOMAIN_TEMPLATES.get(domain.lower())


# Public API ----------------------------------------------------------------------


def generate_peer_review(manuscript: Manuscript) -> ReviewReport:
    """Generate a structured peer review report for ``manuscript``.

    The report contains categorized :class:`ReviewIssue` objects covering
    clarity and coherence, statistical and methodological red flags, missing
    citations, and claims-vs-evidence alignment. When ``manuscript.domain``
    matches a known domain, an adaptive template is applied and surfaced in
    the report summary.

    Parameters
    ----------
    manuscript:
        The manuscript under review.

    Returns
    -------
    ReviewReport
        Structured review suggestions plus an overall score.
    """
    issues: list[ReviewIssue] = []
    issues.extend(_find_clarity_issues(manuscript))
    issues.extend(_find_statistical_issues(manuscript))
    issues.extend(_find_methodological_issues(manuscript))
    issues.extend(_find_citation_issues(manuscript))
    issues.extend(_find_claims_issues(manuscript))

    template = _resolve_domain(manuscript.domain)
    summary_parts = []
    if template is not None:
        summary_parts.append(template["intro"])
        summary_parts.append(template["checks"])
    else:
        summary_parts.append("Review generated with the generic cross-domain template.")

    report = ReviewReport(
        title=manuscript.title,
        domain=manuscript.domain,
        issues=issues,
        summary=" ".join(summary_parts),
    )
    return report


def peer_review_score(report: ReviewReport) -> int:
    """Return the 0-100 score of a :class:`ReviewReport`.

    The score starts at 100 and deducts points weighted by issue severity
    (errors weigh more than warnings, which weigh more than informational
    notes).

    Parameters
    ----------
    report:
        The review report to score.

    Returns
    -------
    int
        Score between 0 and 100.
    """
    return report.score