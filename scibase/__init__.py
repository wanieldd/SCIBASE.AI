"""AI-Powered Research Assistant Suite.

A self-contained toolkit that augments scientific workflows with:

- Auto peer review reports (:mod:`scibase.review`)
- A reproducibility checker (:mod:`scibase.reproducibility`)
- A research gap finder (:mod:`scibase.gap_finder`)

All modules use only the Python standard library so the suite runs anywhere.
"""

from .gap_finder import GapFinder, Paper, ResearchOpportunity
from .reproducibility import (
    Project,
    ReproducibilityIssue,
    ReproducibilityReport,
    ReproducibilityChecker,
)
from .review import (
    Manuscript,
    ReviewCategory,
    ReviewIssue,
    ReviewReport,
    generate_peer_review,
    peer_review_score,
)

__all__ = [
    "GapFinder",
    "Manuscript",
    "Paper",
    "Project",
    "ReproducibilityChecker",
    "ReproducibilityIssue",
    "ReproducibilityReport",
    "ResearchOpportunity",
    "ReviewCategory",
    "ReviewIssue",
    "ReviewReport",
    "generate_peer_review",
    "peer_review_score",
]

__version__ = "0.1.0"