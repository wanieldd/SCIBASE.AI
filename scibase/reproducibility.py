"""Reproducibility checker.

Inspects a project directory to verify output consistency with reported
results, dependency/version integrity, and the presence of raw data, clean
pipelines, and test sets. Flags discrepancies or non-determinism and assigns a
reproducibility confidence score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PIPELINE_EXTENSIONS = {".py", ".ipynb", ".r", ".jl"}
DATA_EXTENSIONS = {".csv", ".tsv", ".json", ".jsonl", ".parquet", ".h5", ".hdf5", ".npy", ".npz"}


@dataclass
class ReproducibilityIssue:
    """A single discrepancy found by the checker.

    Parameters
    ----------
    code:
        Stable machine-readable identifier for the issue.
    message:
        Human-readable description of the problem.
    """

    code: str
    message: str


@dataclass
class Project:
    """A research project to check for reproducibility.

    Parameters
    ----------
    name:
        Project name.
    root:
        Directory containing the project files.
    reported_results:
        Optional mapping of output name -> reported value (as string). When
        an output file is present, the checker compares its contents against
        the reported value.
    dependencies:
        Optional mapping of dependency name -> version. Dependencies without
        a version are flagged as unpinned.
    """

    name: str
    root: Path
    reported_results: dict[str, str] = field(default_factory=dict)
    dependencies: dict[str, str | None] = field(default_factory=dict)


@dataclass
class ReproducibilityReport:
    """Result of running the reproducibility checker over a :class:`Project`.

    Attributes
    ----------
    project:
        The project that was checked.
    issues:
        Discrepancies and missing requirements found.
    checks_passed:
        Names of the checks that passed.
    score:
        Reproducibility confidence score from 0.0 to 1.0.
    """

    project: Project
    issues: list[ReproducibilityIssue] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    score: float = 1.0

    @property
    def reproducible(self) -> bool:
        """True when every hard requirement passes (score above 0.5)."""
        return self.score >= 0.5


class ReproducibilityChecker:
    """Runs reproducibility checks against a :class:`Project` directory."""

    def check(self, project: Project) -> ReproducibilityReport:
        """Check ``project`` and return a :class:`ReproducibilityReport`.

        The following checks are performed:

        - **Pipeline presence**: at least one source or notebook file exists.
        - **Raw data present**: at least one raw data file exists under a
          ``data/`` directory.
        - **Tests present**: at least one test file exists.
        - **Output consistency**: when a reported result names a file, the
          file must exist and its contents must match the reported value.
        - **Dependency integrity**: every dependency must have a pinned
          version.
        - **Determinism**: when a ``reproducibility/runs/`` directory exists,
          each output file must be byte-identical across runs.

        Parameters
        ----------
        project:
            The project to check.

        Returns
        -------
        ReproducibilityReport
            Issues found plus a confidence score in ``[0.0, 1.0]``.
        """
        root = project.root
        issues: list[ReproducibilityIssue] = []
        passed: list[str] = []

        pipeline_files = self._find_pipeline_files(root)
        if pipeline_files:
            passed.append("pipeline")
        else:
            issues.append(
                ReproducibilityIssue(
                    "no-pipeline",
                    "No source or notebook files found; a clean pipeline is required.",
                )
            )

        data_files = self._find_data_files(root)
        if data_files:
            passed.append("raw-data")
        else:
            issues.append(
                ReproducibilityIssue(
                    "no-raw-data",
                    "No raw data files found under a data/ directory.",
                )
            )

        test_files = self._find_test_files(root)
        if test_files:
            passed.append("tests")
        else:
            issues.append(
                ReproducibilityIssue(
                    "no-tests",
                    "No test files found.",
                )
            )

        issues.extend(self._check_output_consistency(project))
        if not any(i.code == "output-mismatch" for i in issues):
            passed.append("output-consistency")

        issues.extend(self._check_dependencies(project))
        if not any(i.code == "unpinned-dependency" for i in issues):
            passed.append("dependencies")

        issues.extend(self._check_determinism(root))
        if not any(i.code == "non-deterministic" for i in issues):
            passed.append("determinism")

        score = self._score(issues)
        return ReproducibilityReport(project=project, issues=issues, checks_passed=passed, score=score)

    # Internal helpers ---------------------------------------------------------

    @staticmethod
    def _find_pipeline_files(root: Path) -> list[Path]:
        if not root.exists():
            return []
        return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in PIPELINE_EXTENSIONS]

    @staticmethod
    def _find_data_files(root: Path) -> list[Path]:
        if not root.exists():
            return []
        data_root = root / "data"
        if not data_root.exists():
            return []
        return [p for p in data_root.rglob("*") if p.is_file() and p.suffix.lower() in DATA_EXTENSIONS]

    @staticmethod
    def _find_test_files(root: Path) -> list[Path]:
        if not root.exists():
            return []
        return [p for p in root.rglob("*") if p.is_file() and (p.name.startswith("test_") or p.name.startswith("tests/"))]

    def _check_output_consistency(self, project: Project) -> list[ReproducibilityIssue]:
        issues: list[ReproducibilityIssue] = []
        for output_name, reported in project.reported_results.items():
            output_file = project.root / output_name
            if not output_file.exists():
                issues.append(
                    ReproducibilityIssue(
                        "missing-output",
                        f"Reported output {output_name!r} does not exist.",
                    )
                )
                continue
            actual = output_file.read_text(encoding="utf-8").strip()
            if actual != reported.strip():
                issues.append(
                    ReproducibilityIssue(
                        "output-mismatch",
                        (
                            f"Reported output {output_name!r} does not match the file contents "
                            f"(reported {reported.strip()!r}, found {actual!r})."
                        ),
                    )
                )
        return issues

    def _check_dependencies(self, project: Project) -> list[ReproducibilityIssue]:
        issues: list[ReproducibilityIssue] = []
        for dep, version in project.dependencies.items():
            if not version:
                issues.append(
                    ReproducibilityIssue(
                        "unpinned-dependency",
                        f"Dependency {dep!r} is not pinned to a version.",
                    )
                )
        return issues

    def _check_determinism(self, root: Path) -> list[ReproducibilityIssue]:
        issues: list[ReproducibilityIssue] = []
        runs_dir = root / "reproducibility" / "runs"
        if not runs_dir.exists():
            return issues

        run_outputs: dict[str, set[bytes]] = {}
        for run in sorted(runs_dir.iterdir()):
            if not run.is_dir():
                continue
            for output in run.rglob("*"):
                if not output.is_file():
                    continue
                run_outputs.setdefault(output.name, set()).add(output.read_bytes())

        for output_name, contents in run_outputs.items():
            if len(contents) > 1:
                issues.append(
                    ReproducibilityIssue(
                        "non-deterministic",
                        f"Output {output_name!r} differs across reproducibility runs.",
                    )
                )
        return issues

    @staticmethod
    def _score(issues: list[ReproducibilityIssue]) -> float:
        if not issues:
            return 1.0
        deduction = 0.2 * len(issues)
        return round(max(0.0, min(1.0, 1.0 - deduction)), 2)