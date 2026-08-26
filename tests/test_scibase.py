"""Tests for the AI-Powered Research Assistant Suite."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scibase.gap_finder import GapFinder, Paper, ResearchOpportunity, extract_questions
from scibase.reproducibility import Project, ReproducibilityChecker
from scibase.review import (
    Manuscript,
    ReviewCategory,
    ReviewReport,
    generate_peer_review,
    peer_review_score,
)


# ---------------------------------------------------------------------------
# 1. Auto peer review reports
# ---------------------------------------------------------------------------


class TestPeerReview:
    def test_clean_manuscript_scores_100(self):
        manuscript = Manuscript(
            title="A complete study",
            abstract=(
                "We measured the growth rate of 120 cell cultures over 30 days. "
                "The mean growth rate was 0.42 (p = 0.023). We found a strong "
                "correlation between growth and temperature (r = 0.81). The "
                "response rate of the follow-up survey was 73 percent."
            ),
            body=(
                "Methods: samples were collected and analyzed. Results confirm "
                "the hypothesized effect in a carefully controlled setting. "
                "The effect size remained consistent across repeated trials."
            ),
            claims=[
                ("Growth rate is temperature dependent.", "Measured r = 0.81 across 120 cultures."),
            ],
            citations=["Smith et al., 2021", "Jones & Doe, 2022"],
        )
        report = generate_peer_review(manuscript)
        assert report.title == "A complete study"
        assert report.score == 100
        assert report.issues == []

    def test_missing_citations_flagged(self):
        manuscript = Manuscript(
            title="No citations",
            abstract="We measured the growth rate of 120 cultures over 30 days.",
            body="The growth rate is shown to be temperature dependent.",
        )
        report = generate_peer_review(manuscript)
        assert any(i.category == ReviewCategory.CITATION for i in report.issues)
        assert any(i.severity == "error" for i in report.issues if i.category == ReviewCategory.CITATION)

    def test_unsupported_claim_flagged(self):
        manuscript = Manuscript(
            title="Unsupported claim",
            abstract="We measured the growth rate of 120 cultures over 30 days.",
            claims=[("This treatment cures the disease.", None)],
            citations=["Smith et al., 2021"],
        )
        report = generate_peer_review(manuscript)
        claims_issues = [i for i in report.issues if i.category == ReviewCategory.CLAIMS]
        assert any("cures the disease" in i.message for i in claims_issues)
        assert all(i.severity == "error" for i in claims_issues)

    def test_statistical_red_flag_unreported_pvalue(self):
        manuscript = Manuscript(
            title="Statistical red flag",
            abstract="A significant p-value was observed.",
            body="The p-value was below the threshold.",
            citations=["Smith et al., 2021"],
        )
        report = generate_peer_review(manuscript)
        stats = [i for i in report.issues if i.category == ReviewCategory.STATISTICAL]
        assert any("p-value" in i.message for i in stats)
        assert any(i.severity == "error" for i in stats)

    def test_domain_specific_template(self):
        manuscript = Manuscript(
            title="Clinical trial",
            abstract="We measured the growth rate of 120 cultures over 30 days.",
            body="",
            domain="clinical-trials",
            citations=["Smith et al., 2021"],
        )
        report = generate_peer_review(manuscript)
        assert "clinical trial reporting standards" in report.summary

    def test_unknown_domain_falls_back_to_generic(self):
        manuscript = Manuscript(
            title="Weird domain",
            abstract="We measured the growth rate of 120 cultures over 30 days.",
            domain="alchemy",
        )
        report = generate_peer_review(manuscript)
        assert "generic cross-domain template" in report.summary

    def test_score_deductions(self):
        errors = [Manuscript(
            title="x",
            abstract="t",
            body="",
        )]
        clean = Manuscript(
            title="clean",
            abstract="We measured the growth rate of 120 cultures over 30 days.",
            body="",
            citations=["a", "b"],
        )
        bad_score = peer_review_score(generate_peer_review(errors[0]))
        good_score = peer_review_score(generate_peer_review(clean))
        assert bad_score < good_score
        assert 0 <= bad_score <= 100

    def test_report_is_review_report_type(self):
        report = generate_peer_review(Manuscript(title="t", abstract="a"))
        assert isinstance(report, ReviewReport)


# ---------------------------------------------------------------------------
# 2. Reproducibility checker
# ---------------------------------------------------------------------------


class TestReproducibility:
    def _write_pipeline(self, tmp_path):
        (tmp_path / "analysis.py").write_text("print('done')\n")
        data = tmp_path / "data"
        data.mkdir()
        (data / "raw.csv").write_text("x,y\n1,2\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_analysis.py").write_text("def test_x(): pass\n")

    def test_complete_project_scores_full(self, tmp_path):
        self._write_pipeline(tmp_path)
        (tmp_path / "results.txt").write_text("accuracy=0.94\n")

        project = Project(
            name="complete",
            root=tmp_path,
            reported_results={"results.txt": "accuracy=0.94"},
            dependencies={"numpy": "1.26.4", "pandas": "2.2.2"},
        )
        report = ReproducibilityChecker().check(project)
        assert report.score == 1.0
        assert report.reproducible
        assert set(report.checks_passed) == {
            "pipeline",
            "raw-data",
            "tests",
            "output-consistency",
            "dependencies",
            "determinism",
        }

    def test_missing_pipeline_and_data_flagged(self, tmp_path):
        project = Project(name="empty", root=tmp_path)
        report = ReproducibilityChecker().check(project)
        codes = {i.code for i in report.issues}
        assert {"no-pipeline", "no-raw-data", "no-tests"} <= codes
        assert report.score == 0.4
        assert not report.reproducible

    def test_output_mismatch_flagged(self, tmp_path):
        self._write_pipeline(tmp_path)
        (tmp_path / "results.txt").write_text("accuracy=0.91\n")

        project = Project(
            name="mismatch",
            root=tmp_path,
            reported_results={"results.txt": "accuracy=0.94"},
        )
        report = ReproducibilityChecker().check(project)
        assert any(i.code == "output-mismatch" for i in report.issues)
        assert "output-consistency" not in report.checks_passed

    def test_missing_reported_output_flagged(self, tmp_path):
        self._write_pipeline(tmp_path)

        project = Project(
            name="missing-output",
            root=tmp_path,
            reported_results={"results.txt": "accuracy=0.94"},
        )
        report = ReproducibilityChecker().check(project)
        assert any(i.code == "missing-output" for i in report.issues)

    def test_unpinned_dependency_flagged(self, tmp_path):
        self._write_pipeline(tmp_path)

        project = Project(
            name="unpinned",
            root=tmp_path,
            dependencies={"numpy": None},
        )
        report = ReproducibilityChecker().check(project)
        assert any(i.code == "unpinned-dependency" for i in report.issues)
        assert "dependencies" not in report.checks_passed

    def test_non_determinism_detected(self, tmp_path):
        self._write_pipeline(tmp_path)

        runs = tmp_path / "reproducibility" / "runs"
        (runs / "run1").mkdir(parents=True)
        (runs / "run2").mkdir(parents=True)
        (runs / "run1" / "output.txt").write_text("same\n")
        (runs / "run2" / "output.txt").write_text("different\n")

        project = Project(name="non-deterministic", root=tmp_path)
        report = ReproducibilityChecker().check(project)
        assert any(i.code == "non-deterministic" for i in report.issues)
        assert "determinism" not in report.checks_passed

    def test_deterministic_runs_pass(self, tmp_path):
        self._write_pipeline(tmp_path)

        runs = tmp_path / "reproducibility" / "runs"
        (runs / "run1").mkdir(parents=True)
        (runs / "run2").mkdir(parents=True)
        (runs / "run1" / "output.txt").write_text("same\n")
        (runs / "run2" / "output.txt").write_text("same\n")

        project = Project(name="deterministic", root=tmp_path)
        report = ReproducibilityChecker().check(project)
        assert "determinism" in report.checks_passed
        assert not any(i.code == "non-deterministic" for i in report.issues)


# ---------------------------------------------------------------------------
# 3. Research gap finder
# ---------------------------------------------------------------------------


def _corpus() -> list[Paper]:
    return [
        Paper(
            id="p1",
            title="CRISPR screens in single-cell RNA-seq",
            abstract="",
            topics=["CRISPR", "Alzheimer's", "single-cell RNA-seq"],
            citations=40,
            open_questions=["The role of glia remains unclear.", "Future work should map cell states."],
        ),
        Paper(
            id="p2",
            title="Single-cell atlas of Alzheimer's",
            abstract="",
            topics=["Alzheimer's", "single-cell RNA-seq"],
            citations=30,
        ),
        Paper(
            id="p3",
            title="CRISPR for gene therapy",
            abstract="",
            topics=["CRISPR", "gene therapy"],
            citations=25,
        ),
        Paper(
            id="p4",
            title="CRISPR editing in neurons",
            abstract="",
            topics=["CRISPR", "Alzheimer's"],
            citations=20,
        ),
        Paper(
            id="p5",
            title="Single-cell methods review",
            abstract="",
            topics=["single-cell RNA-seq"],
            citations=10,
        ),
        Paper(
            id="p6",
            title="Gene therapy trial",
            abstract="",
            topics=["gene therapy"],
            citations=3,
        ),
        Paper(
            id="p7",
            title="Alzheimer's pathology",
            abstract="",
            topics=["Alzheimer's"],
            citations=15,
        ),
    ]


class TestGapFinder:
    def test_topic_popularity(self):
        finder = GapFinder(_corpus())
        popularity = finder.topic_popularity()
        assert popularity["CRISPR"] == 3
        assert popularity["Alzheimer's"] == 4
        assert popularity["single-cell RNA-seq"] == 3
        assert popularity["gene therapy"] == 2

    def test_under_studied_intersection_found(self):
        finder = GapFinder(_corpus())
        opportunities = finder.under_studied_intersections()
        combos = {o.topics for o in opportunities}
        # CRISPR + single-cell RNA-seq never co-occur in the corpus
        assert frozenset({"CRISPR", "single-cell RNA-seq"}) in combos
        # but gene therapy is not active enough to qualify
        assert all("gene therapy" not in o.topics for o in opportunities)
        assert opportunities == sorted(opportunities, key=lambda o: o.score, reverse=True)

    def test_saturated_intersection_excluded(self):
        papers = [
            Paper(id="a", title="a", topics=["X", "Y"], citations=10),
            Paper(id="b", title="b", topics=["X", "Y"], citations=10),
            Paper(id="c", title="c", topics=["X"], citations=10),
            Paper(id="d", title="d", topics=["Y"], citations=10),
        ]
        finder = GapFinder(papers)
        opportunities = finder.under_studied_intersections()
        # every paper covering X or Y already covers both -> no gap
        assert all(frozenset({"X", "Y"}) != o.topics for o in opportunities)

    def test_unresolved_questions(self):
        finder = GapFinder(_corpus())
        questions = finder.unresolved_questions(min_citations=5)
        assert any(q.startswith("The role of glia") for q, _, _ in questions)
        assert all(total >= 5 for _, _, total in questions)
        # sorted by total citations descending
        assert questions == sorted(questions, key=lambda item: item[2], reverse=True)

    def test_research_opportunities_feed_personalized(self):
        finder = GapFinder(_corpus())
        feed = finder.research_opportunities_feed(
            interests=["single-cell RNA-seq"],
            project_history=["CRISPR"],
        )
        assert feed
        assert all(o.relevance >= 1 for o in feed)
        assert all(o.topics & {"single-cell RNA-seq", "CRISPR"} for o in feed)
        assert feed == sorted(feed, key=lambda o: o.score, reverse=True)

    def test_feed_excludes_irrelevant_gaps(self):
        finder = GapFinder(_corpus())
        feed = finder.research_opportunities_feed(
            interests=["gene therapy"],
            project_history=[],
        )
        assert feed == []

    def test_extract_questions(self):
        text = (
            "The mechanism remains unclear. "
            "Future work should address this. "
            "Results were conclusive."
        )
        questions = extract_questions(text)
        assert len(questions) == 2
        assert "remains unclear" in questions[0]

    def test_opportunity_score(self):
        opportunity = ResearchOpportunity(
            topics=frozenset({"CRISPR", "single-cell RNA-seq"}),
            popularity={"CRISPR": 3, "single-cell RNA-seq": 3},
            combination_count=0,
            rationale="never co-occur",
            relevance=2,
        )
        # (3 + 3) * (1 + 2) / (1 + 0) = 18
        assert opportunity.score == 18.0