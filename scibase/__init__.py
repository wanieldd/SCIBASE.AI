"""Scientific Bounty System.

A self-contained toolkit that turns the platform into a global research
marketplace by connecting real-world R&D challenges with scientific talent:

- A challenge posting portal (:mod:`scibase.bounty`)
- A submission engine with package manifests
- Arbitration and escrowed reward distribution

All modules use only the Python standard library so the suite runs anywhere.
"""

from .bounty import (
    Arbiter,
    ArbitrationReport,
    Challenge,
    ChallengeVisibility,
    DeliverableCheck,
    GENERIC_TEMPLATE,
    IPOption,
    Payout,
    PayoutEngine,
    PayoutStatus,
    RND_TEMPLATES,
    Submission,
    SubmissionPackageBuilder,
    SubmissionPhase,
    challenge_template,
    ip_terms,
)

__all__ = [
    "Arbiter",
    "ArbitrationReport",
    "Challenge",
    "ChallengeVisibility",
    "DeliverableCheck",
    "GENERIC_TEMPLATE",
    "IPOption",
    "Payout",
    "PayoutEngine",
    "PayoutStatus",
    "RND_TEMPLATES",
    "Submission",
    "SubmissionPackageBuilder",
    "SubmissionPhase",
    "challenge_template",
    "ip_terms",
]

__version__ = "0.1.0"