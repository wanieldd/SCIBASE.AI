"""Scientific Bounty System.

A self-contained reference implementation of the bounty marketplace that
connects real-world R&D challenges from industry, government, and nonprofits
with the scientific talent able to solve them. It covers the three core
capabilities of the platform:

- The **challenge posting portal** (:class:`Challenge`) for organizations to
  describe problems, deliverables, evaluation rubrics, timelines, and prizes.
- The **submission engine** (:class:`Submission`,
  :class:`SubmissionPackageBuilder`) giving each team a private, versioned
  project space with an automated package manifest.
- **Arbitration & reward distribution** (:class:`Arbiter`,
  :class:`PayoutEngine`) for platform-mediated validation, escrowed prize
  funds, partial milestone payouts, and IP management.

Only the Python standard library is used so the module runs anywhere.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ChallengeVisibility(str, Enum):
    """Whether a challenge is visible to everyone or invitation only."""

    PUBLIC = "public"
    PRIVATE = "private"


class IPOption(str, Enum):
    """Intellectual property terms for a challenge.

    - ``SOLVER_RETAINS`` — the solver keeps IP until paid (the default).
    - ``SPONSORED_TRANSFER`` — IP transfers to the sponsor upon payout, with a
      licensing option available.
    - ``OPEN_SOURCE`` — all submissions are open-sourced under predefined
      terms.
    """

    SOLVER_RETAINS = "solver-retains"
    SPONSORED_TRANSFER = "sponsored-transfer"
    OPEN_SOURCE = "open-source"


class SubmissionPhase(str, Enum):
    """Phases of a multi-phase challenge (proposal → prototype → final)."""

    PROPOSAL = "proposal"
    PROTOTYPE = "prototype"
    FINAL = "final"


class PayoutStatus(str, Enum):
    """Lifecycle of an escrowed payout."""

    ESCROWED = "escrowed"
    SCHEDULED = "scheduled"
    PAID = "paid"
    RELEASED = "released"


# R&D vertical templates for the challenge posting portal -----------------------

RND_TEMPLATES: dict[str, dict[str, str]] = {
    "biotech": {
        "name": "Biotech",
        "deliverables": "validated assay, cell or animal model, experimental dataset",
        "criteria": "statistical rigor, reproducibility, clinical relevance",
    },
    "materials": {
        "name": "Materials Science",
        "deliverables": "synthesized sample, characterization dataset, processing protocol",
        "criteria": "measured properties, purity, scalability",
    },
    "climate": {
        "name": "Climate & Earth Science",
        "deliverables": "forecasting model, regional dataset, validation report",
        "criteria": "forecast skill, calibration, operational readiness",
    },
    "ml": {
        "name": "Machine Learning",
        "deliverables": "trained model, code and weights, evaluation notebook",
        "criteria": "benchmark scores, generalization, efficiency",
    },
    "chemistry": {
        "name": "Chemistry",
        "deliverables": "synthetic route, purified compound, analytical data",
        "criteria": "yield, purity, safety",
    },
}

GENERIC_TEMPLATE: dict[str, str] = {
    "name": "Generic R&D",
    "deliverables": "working model, dataset, or whitepaper",
    "criteria": "technical quality, clarity, impact",
}


def challenge_template(domain: str) -> dict[str, str]:
    """Return the R&D template for ``domain``, or a generic fallback.

    Templates are available for biotech, materials, climate, ML, chemistry,
    and other verticals. Unknown domains fall back to ``GENERIC_TEMPLATE``.
    """
    return RND_TEMPLATES.get(domain.lower(), GENERIC_TEMPLATE)


# 1. Challenge posting portal ----------------------------------------------------


@dataclass
class Challenge:
    """A scientific or technical challenge posted by an organization.

    Parameters
    ----------
    id:
        Unique challenge identifier.
    title:
        Short public title for the challenge.
    organization:
        The posting organization (industry, government, or nonprofit).
    description:
        Problem description.
    scientific_context:
        Scientific background motivating the problem.
    deliverables:
        Expected deliverables (e.g. working model, dataset, whitepaper).
    evaluation_criteria:
        Scoring rubric mapping criterion names to weights that sum to 1.0.
    milestones:
        Timeline of milestone deadlines (``datetime.date`` objects).
    prize_amount:
        Total prize amount offered.
    payout_schedule:
        Amount paid out at each milestone; must sum to ``prize_amount``.
    visibility:
        ``ChallengeVisibility.PUBLIC`` or ``ChallengeVisibility.PRIVATE``.
    domain:
        Optional R&D vertical (e.g. ``"ml"``) used to pick a template.
    qualification_rounds:
        Whether pre-qualification rounds are required.
    nda:
        Whether an NDA is required for sensitive topics.
    ip_option:
        Intellectual property terms (see :class:`IPOption`).
    status:
        Lifecycle state of the challenge (e.g. ``"open"``, ``"closed"``).
    """

    id: str
    title: str
    organization: str
    description: str
    scientific_context: str
    deliverables: list[str]
    evaluation_criteria: dict[str, float]
    milestones: list[date]
    prize_amount: float
    payout_schedule: list[float]
    visibility: ChallengeVisibility = ChallengeVisibility.PUBLIC
    domain: str | None = None
    qualification_rounds: bool = False
    nda: bool = False
    ip_option: IPOption = IPOption.SOLVER_RETAINS
    status: str = "open"

    def validate(self) -> list[str]:
        """Check required components; an empty list means the challenge is valid.

        Validates the problem description and scientific context, at least one
        deliverable, an evaluation rubric whose weights sum to 1.0, at least
        one milestone deadline, and a payout schedule matching the prize.
        """
        problems: list[str] = []
        if not self.description.strip():
            problems.append("challenge requires a problem description")
        if not self.scientific_context.strip():
            problems.append("challenge requires scientific context")
        if not self.deliverables:
            problems.append("challenge requires at least one deliverable")
        if not self.evaluation_criteria:
            problems.append("challenge requires evaluation criteria and a scoring rubric")
        elif abs(sum(self.evaluation_criteria.values()) - 1.0) > 1e-9:
            problems.append("evaluation criterion weights must sum to 1.0")
        if not self.milestones:
            problems.append("challenge requires a timeline with milestone deadlines")
        if abs(sum(self.payout_schedule) - self.prize_amount) > 1e-9:
            problems.append("payout schedule must sum to the prize amount")
        return problems

    @property
    def template(self) -> dict[str, str]:
        """The R&D template used for this challenge's domain."""
        return challenge_template(self.domain or "")


# 2. Submission engine -----------------------------------------------------------


@dataclass
class Submission:
    """A team's private, versioned project space for a challenge.

    Parameters
    ----------
    id:
        Unique submission identifier.
    challenge_id:
        The challenge this submission answers.
    team_name:
        Display name; may be empty when participation is anonymous.
    anonymous:
        Whether participation is anonymous.
    phase:
        Current phase of a multi-phase challenge.
    deliverables:
        Deliverables submitted so far, keyed by artifact name.
    status:
        Lifecycle state (e.g. ``"draft"``, ``"submitted"``).
    """

    id: str
    challenge_id: str
    team_name: str = ""
    anonymous: bool = False
    phase: SubmissionPhase = SubmissionPhase.PROPOSAL
    deliverables: dict[str, str] = field(default_factory=dict)
    status: str = "draft"
    _versions: list[tuple[str, str]] = field(default_factory=list, repr=False)

    def add_deliverable(self, name: str, artifact: str) -> None:
        """Record a deliverable and append an audit-log entry."""
        self.deliverables[name] = artifact
        self._versions.append((name, "added"))

    def advance_phase(self) -> None:
        """Advance to the next challenge phase (proposal → prototype → final)."""
        order = [SubmissionPhase.PROPOSAL, SubmissionPhase.PROTOTYPE, SubmissionPhase.FINAL]
        index = order.index(self.phase)
        if index < len(order) - 1:
            self.phase = order[index + 1]

    @property
    def audit_log(self) -> list[tuple[str, str]]:
        """Version control / audit log entries for reproducibility."""
        return list(self._versions)


class SubmissionPackageBuilder:
    """Built-in submission package builder.

    Produces the automated manifest of deliverables for a submission so
    sponsors receive a standardized package.
    """

    def build_manifest(self, submission: Submission) -> dict[str, dict[str, str]]:
        """Build a manifest mapping each deliverable to its artifact and hash.

        Each entry contains the recorded ``artifact`` reference and a
        ``sha256`` digest of its contents, giving a verifiable fingerprint of
        the submitted package.
        """
        manifest: dict[str, dict[str, str]] = {}
        for name in sorted(submission.deliverables):
            artifact = submission.deliverables[name]
            digest = hashlib.sha256(artifact.encode("utf-8")).hexdigest()
            manifest[name] = {"artifact": artifact, "sha256": digest}
        return manifest


# 3. Arbitration & reward distribution -------------------------------------------


@dataclass
class DeliverableCheck:
    """Result of one automated arbitration checklist item."""

    deliverable: str
    present: bool
    passed: bool
    note: str


@dataclass
class ArbitrationReport:
    """Outcome of arbitration for a submission against a challenge."""

    challenge_id: str
    submission_id: str
    checks: list[DeliverableCheck]
    score: float
    passed: bool
    reviewer: str | None = None
    feedback: list[str] = field(default_factory=list)

    @property
    def missing(self) -> list[str]:
        """Deliverables that are required but absent from the submission."""
        return [check.deliverable for check in self.checks if not check.present]


class Arbiter:
    """Platform-mediated arbitration between sponsors and submitters.

    Runs an automated checklist verifying each required deliverable is present
    and scores the submission. An optional third-party reviewer can be
    attached for peer validation.
    """

    def arbitrate(
        self,
        challenge: Challenge,
        submission: Submission,
        reviewer: str | None = None,
    ) -> ArbitrationReport:
        """Arbitrate ``submission`` against ``challenge``.

        Returns an :class:`ArbitrationReport` whose ``score`` is the fraction
        of required deliverables present (0.0-1.0) and whose ``passed`` flag
        is true only when every required deliverable is present.
        """
        checks: list[DeliverableCheck] = []
        for name in challenge.deliverables:
            present = name in submission.deliverables
            checks.append(
                DeliverableCheck(
                    deliverable=name,
                    present=present,
                    passed=present,
                    note="present" if present else "missing",
                )
            )

        total = len(checks)
        present_count = sum(1 for check in checks if check.present)
        score = present_count / total if total else 0.0
        passed = present_count == total

        feedback: list[str] = []
        missing = [check.deliverable for check in checks if not check.present]
        if missing:
            feedback.append(f"missing deliverables: {', '.join(missing)}")
        if reviewer is not None:
            feedback.append(f"reviewed by third-party validator: {reviewer}")

        return ArbitrationReport(
            challenge_id=challenge.id,
            submission_id=submission.id,
            checks=checks,
            score=score,
            passed=passed,
            reviewer=reviewer,
            feedback=feedback,
        )


@dataclass
class Payout:
    """A single scheduled payout to a solver."""

    submission_id: str
    amount: float
    route: str
    reason: str
    status: PayoutStatus = PayoutStatus.SCHEDULED


class PayoutEngine:
    """Escrowed smart payout engine for reward distribution.

    Prize funds are escrowed per challenge. Payouts can be partial (milestone
    payments or honorable mentions) and are routed to individuals, teams, or
    institutions. Leftover escrow is released back to the sponsor when a
    challenge closes.
    """

    def __init__(self) -> None:
        self._escrow: dict[str, float] = {}
        self._payouts: list[Payout] = []

    def escrow(self, challenge_id: str, amount: float) -> float:
        """Deposit ``amount`` into escrow for a challenge."""
        self._escrow[challenge_id] = self._escrow.get(challenge_id, 0.0) + amount
        return self._escrow[challenge_id]

    def funds_available(self, challenge_id: str) -> float:
        """Escrowed funds remaining for a challenge."""
        return self._escrow.get(challenge_id, 0.0)

    def schedule(
        self,
        challenge_id: str,
        submission_id: str,
        amount: float,
        route: str,
        reason: str = "final",
    ) -> Payout:
        """Schedule a payout, rejecting any request beyond escrowed funds."""
        available = self.funds_available(challenge_id)
        if amount > available + 1e-9:
            raise ValueError(
                f"payout of {amount} exceeds escrowed funds ({available}) "
                f"for challenge {challenge_id}"
            )
        self._escrow[challenge_id] = available - amount
        payout = Payout(
            submission_id=submission_id,
            amount=amount,
            route=route,
            reason=reason,
        )
        self._payouts.append(payout)
        return payout

    def pay(self, payout: Payout) -> None:
        """Mark a scheduled payout as paid."""
        if payout.status is PayoutStatus.PAID:
            return
        payout.status = PayoutStatus.PAID

    def release_escrow(self, challenge_id: str) -> float:
        """Return leftover escrow to the sponsor when a challenge closes."""
        leftover = self.funds_available(challenge_id)
        self._escrow[challenge_id] = 0.0
        if leftover:
            self._payouts.append(
                Payout(
                    submission_id="escrow-release",
                    amount=leftover,
                    route="sponsor",
                    reason="escrow-release",
                    status=PayoutStatus.RELEASED,
                )
            )
        return leftover

    @property
    def payouts(self) -> list[Payout]:
        """All payouts scheduled or paid by this engine."""
        return list(self._payouts)


# IP management ------------------------------------------------------------------


def ip_terms(ip_option: IPOption) -> str:
    """Human-readable IP terms for an :class:`IPOption`."""
    return {
        IPOption.SOLVER_RETAINS: "solver retains IP until paid",
        IPOption.SPONSORED_TRANSFER: "IP transfers to the sponsor upon payout with a licensing option",
        IPOption.OPEN_SOURCE: "all submissions open-sourced under predefined terms",
    }[ip_option]