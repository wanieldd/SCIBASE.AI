# Scientific Bounty System

A self-contained toolkit that transforms the platform into a global research
marketplace, connecting real-world R&D challenges from industry, government,
and nonprofits with the scientific talent capable of solving them. The system
is dependency-free (Python standard library only) and ships with a full pytest
suite.

## Capabilities

### 1. Challenge Posting Portal — `scibase.bounty.Challenge`

Organizations post scientific or technical challenges with all required
components: a problem description and scientific context, deliverables,
evaluation criteria (scoring rubric), a milestone timeline, and a prize amount
with payout schedule. `Challenge.validate()` returns an empty list only when
the posting is complete and internally consistent (rubric weights sum to 1.0,
payout schedule matches the prize).

Optional features are supported as flags: public vs. private visibility,
pre-qualification rounds, NDA support for sensitive topics, and IP terms.
Templates for R&D verticals (biotech, materials, climate, ML, chemistry) are
available via `challenge_template(domain)`; unknown domains fall back to a
generic template.

```python
from datetime import date
from scibase import Challenge, ChallengeVisibility, IPOption

challenge = Challenge(
    id="C1",
    title="Regional climate forecasting prize",
    organization="Climate Nonprofit",
    description="Best regional forecasting model wins the prize.",
    scientific_context="Regional skill scores lag global models.",
    deliverables=["model", "dataset", "report"],
    evaluation_criteria={"accuracy": 0.5, "novelty": 0.3, "reproducibility": 0.2},
    milestones=[date(2026, 9, 1), date(2026, 12, 1)],
    prize_amount=100_000.0,
    payout_schedule=[30_000.0, 70_000.0],
    visibility=ChallengeVisibility.PUBLIC,
    domain="climate",
    nda=True,
    ip_option=IPOption.SOLVER_RETAINS,   # default: solver keeps IP until paid
)
assert challenge.validate() == []
print(challenge.template["name"])        # Climate & Earth Science
```

### 2. Submission Engine — `scibase.bounty.Submission`

Each team gets a private, versioned project space for a challenge. Deliverables
are recorded with an audit log for reproducibility, participation can be
anonymous, and multi-phase challenges (proposal → prototype → final) are
supported via `advance_phase()`.

The `SubmissionPackageBuilder` produces the automated manifest of deliverables
— each entry carries a `sha256` digest of the artifact contents so sponsors
receive a standardized, verifiable package.

```python
from scibase import Submission, SubmissionPhase, SubmissionPackageBuilder

submission = Submission(id="S1", challenge_id="C1", team_name="Lab X")
submission.add_deliverable("model", "weights.h5")
submission.add_deliverable("report", "results.pdf")
submission.advance_phase()
print(submission.phase)                  # SubmissionPhase.PROTOTYPE
print(submission.audit_log)              # [('model', 'added'), ('report', 'added')]

manifest = SubmissionPackageBuilder().build_manifest(submission)
print(manifest["model"]["sha256"])       # 64-char hex digest
```

### 3. Arbitration & Reward Distribution — `scibase.bounty.Arbiter`, `PayoutEngine`

Platform-mediated arbitration runs an automated checklist verifying every
required deliverable is present, producing a 0.0-1.0 score and a pass/fail
flag. An optional third-party reviewer can be attached for peer validation.

The smart payout engine holds prize funds in escrow per challenge, schedules
partial payments for milestones or honorable mentions, routes payouts to
individuals, teams, or institutions, and releases leftover escrow back to the
sponsor when a challenge closes. IP terms are managed via the `IPOption` enum:
solver retains IP until paid (default), sponsored IP transfer with a licensing
option, or open-sourcing of all submissions.

```python
from scibase import Arbiter, PayoutEngine

report = Arbiter().arbitrate(challenge, submission)
print(report.score, report.passed, report.missing)

engine = PayoutEngine()
engine.escrow("C1", 100_000.0)
milestone = engine.schedule("C1", "S1", 30_000.0, route="team", reason="milestone")
engine.pay(milestone)
leftover = engine.release_escrow("C1")
print(engine.funds_available("C1"))      # 0.0 (escrow released)
```

## Running the tests

```bash
python -m pytest tests/ -q
```