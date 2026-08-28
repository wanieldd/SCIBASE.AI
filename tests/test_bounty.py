"""Tests for the Scientific Bounty System."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scibase.bounty import (
    Arbiter,
    Challenge,
    ChallengeVisibility,
    IPOption,
    PayoutEngine,
    PayoutStatus,
    Submission,
    SubmissionPackageBuilder,
    SubmissionPhase,
    challenge_template,
    ip_terms,
)


def _challenge(**overrides) -> Challenge:
    params = dict(
        id="C1",
        title="Single-cell biomarker discovery",
        organization="PharmaCorp",
        description="Identify biomarkers from single-cell RNA-seq data.",
        scientific_context="Differential expression across disease and control samples.",
        deliverables=["model", "dataset", "report"],
        evaluation_criteria={"accuracy": 0.5, "novelty": 0.3, "reproducibility": 0.2},
        milestones=[date(2026, 9, 1), date(2026, 12, 1)],
        prize_amount=100_000.0,
        payout_schedule=[30_000.0, 70_000.0],
    )
    params.update(overrides)
    return Challenge(**params)


# ---------------------------------------------------------------------------
# 1. Challenge posting portal
# ---------------------------------------------------------------------------


class TestChallengePosting:
    def test_valid_challenge_validates_clean(self):
        assert _challenge().validate() == []

    def test_missing_description_and_context_flagged(self):
        problems = _challenge(description="", scientific_context="").validate()
        assert "challenge requires a problem description" in problems
        assert "challenge requires scientific context" in problems

    def test_missing_deliverables_flagged(self):
        problems = _challenge(deliverables=[]).validate()
        assert "challenge requires at least one deliverable" in problems

    def test_rubric_weights_must_sum_to_one(self):
        problems = _challenge(evaluation_criteria={"accuracy": 0.5}).validate()
        assert "evaluation criterion weights must sum to 1.0" in problems

    def test_empty_rubric_flagged(self):
        problems = _challenge(evaluation_criteria={}).validate()
        assert "challenge requires evaluation criteria and a scoring rubric" in problems

    def test_missing_timeline_flagged(self):
        problems = _challenge(milestones=[]).validate()
        assert "challenge requires a timeline with milestone deadlines" in problems

    def test_payout_schedule_must_match_prize(self):
        problems = _challenge(payout_schedule=[10_000.0]).validate()
        assert "payout schedule must sum to the prize amount" in problems

    def test_public_and_private_visibility(self):
        assert _challenge(visibility=ChallengeVisibility.PRIVATE).validate() == []
        assert _challenge(visibility=ChallengeVisibility.PUBLIC).validate() == []

    def test_domain_template_lookup(self):
        assert challenge_template("ml")["name"] == "Machine Learning"
        assert challenge_template("biotech")["name"] == "Biotech"
        assert "deliverables" in challenge_template("climate")

    def test_unknown_domain_falls_back_to_generic(self):
        template = challenge_template("quantum-whale")
        assert template == challenge_template("")
        assert "working model, dataset, or whitepaper" in template["deliverables"]

    def test_challenge_template_property_uses_domain(self):
        assert _challenge(domain="chemistry").template["name"] == "Chemistry"

    def test_ip_terms_default_is_solver_retains(self):
        assert _challenge().ip_option is IPOption.SOLVER_RETAINS
        assert "solver retains IP" in ip_terms(IPOption.SOLVER_RETAINS)
        assert "sponsor upon payout" in ip_terms(IPOption.SPONSORED_TRANSFER)
        assert "open-sourced" in ip_terms(IPOption.OPEN_SOURCE)

    def test_nda_and_qualification_flags(self):
        challenge = _challenge(nda=True, qualification_rounds=True)
        assert challenge.nda and challenge.qualification_rounds


# ---------------------------------------------------------------------------
# 2. Submission engine
# ---------------------------------------------------------------------------


class TestSubmissionEngine:
    def test_add_deliverable_records_audit_entry(self):
        submission = Submission(id="S1", challenge_id="C1", team_name="Lab X")
        submission.add_deliverable("model", "weights.h5")
        assert submission.deliverables == {"model": "weights.h5"}
        assert ("model", "added") in submission.audit_log

    def test_anonymous_participation(self):
        submission = Submission(id="S2", challenge_id="C1", anonymous=True)
        assert submission.anonymous
        assert submission.team_name == ""

    def test_advance_phase_sequence(self):
        submission = Submission(id="S3", challenge_id="C1")
        assert submission.phase is SubmissionPhase.PROPOSAL
        submission.advance_phase()
        assert submission.phase is SubmissionPhase.PROTOTYPE
        submission.advance_phase()
        assert submission.phase is SubmissionPhase.FINAL
        submission.advance_phase()
        assert submission.phase is SubmissionPhase.FINAL

    def test_manifest_builds_verifiable_entries(self):
        submission = Submission(id="S4", challenge_id="C1")
        submission.add_deliverable("report", "results.pdf")
        submission.add_deliverable("model", "weights.h5")
        manifest = SubmissionPackageBuilder().build_manifest(submission)
        assert set(manifest) == {"model", "report"}
        assert manifest["model"]["artifact"] == "weights.h5"
        assert len(manifest["model"]["sha256"]) == 64
        assert manifest["report"]["artifact"] == "results.pdf"

    def test_manifest_is_deterministic(self):
        submission = Submission(id="S5", challenge_id="C1")
        submission.add_deliverable("report", "results.pdf")
        builder = SubmissionPackageBuilder()
        assert builder.build_manifest(submission) == builder.build_manifest(submission)


# ---------------------------------------------------------------------------
# 3. Arbitration & reward distribution
# ---------------------------------------------------------------------------


class TestArbitration:
    def test_complete_submission_passes_with_full_score(self):
        challenge = _challenge()
        submission = Submission(id="S6", challenge_id="C1")
        for name in challenge.deliverables:
            submission.add_deliverable(name, f"{name}.artifact")
        report = Arbiter().arbitrate(challenge, submission)
        assert report.passed
        assert report.score == 1.0
        assert report.missing == []
        assert report.challenge_id == "C1"
        assert report.submission_id == "S6"

    def test_incomplete_submission_fails_and_lists_missing(self):
        challenge = _challenge()
        submission = Submission(id="S7", challenge_id="C1")
        submission.add_deliverable("model", "weights.h5")
        report = Arbiter().arbitrate(challenge, submission)
        assert not report.passed
        assert report.score == pytest.approx(1 / 3)
        assert set(report.missing) == {"dataset", "report"}
        assert any("missing deliverables" in f for f in report.feedback)

    def test_empty_deliverables_challenge_scores_zero(self):
        challenge = _challenge(deliverables=[])
        report = Arbiter().arbitrate(challenge, Submission(id="S8", challenge_id="C1"))
        assert report.score == 0.0
        assert report.passed

    def test_optional_third_party_reviewer_attached(self):
        challenge = _challenge()
        submission = Submission(id="S9", challenge_id="C1")
        for name in challenge.deliverables:
            submission.add_deliverable(name, "x")
        report = Arbiter().arbitrate(challenge, submission, reviewer="Dr. Peer")
        assert report.reviewer == "Dr. Peer"
        assert any("third-party validator" in f for f in report.feedback)


class TestPayoutEngine:
    def test_escrow_and_funds_available(self):
        engine = PayoutEngine()
        engine.escrow("C1", 100_000.0)
        assert engine.funds_available("C1") == 100_000.0
        assert engine.funds_available("C2") == 0.0

    def test_partial_milestone_payout_scheduled(self):
        engine = PayoutEngine()
        engine.escrow("C1", 100_000.0)
        payout = engine.schedule("C1", "S10", 30_000.0, route="team", reason="milestone")
        assert payout.status is PayoutStatus.SCHEDULED
        assert payout.reason == "milestone"
        assert engine.funds_available("C1") == 70_000.0
        assert payout in engine.payouts

    def test_schedule_beyond_escrow_raises(self):
        engine = PayoutEngine()
        engine.escrow("C1", 10_000.0)
        with pytest.raises(ValueError):
            engine.schedule("C1", "S11", 20_000.0, route="individual")

    def test_payout_routes_individual_team_institution(self):
        engine = PayoutEngine()
        engine.escrow("C1", 50_000.0)
        routes = {"individual", "team", "institution"}
        for route in routes:
            engine.schedule("C1", "S12", 1_000.0, route=route)
        assert {p.route for p in engine.payouts} == routes

    def test_pay_marks_paid(self):
        engine = PayoutEngine()
        engine.escrow("C1", 10_000.0)
        payout = engine.schedule("C1", "S13", 10_000.0, route="individual")
        engine.pay(payout)
        assert payout.status is PayoutStatus.PAID

    def test_release_escrow_returns_leftover(self):
        engine = PayoutEngine()
        engine.escrow("C1", 100_000.0)
        engine.schedule("C1", "S14", 60_000.0, route="team")
        leftover = engine.release_escrow("C1")
        assert leftover == 40_000.0
        assert engine.funds_available("C1") == 0.0
        released = [p for p in engine.payouts if p.reason == "escrow-release"]
        assert len(released) == 1
        assert released[0].status is PayoutStatus.RELEASED

    def test_release_empty_escrow_is_zero(self):
        engine = PayoutEngine()
        assert engine.release_escrow("C1") == 0.0