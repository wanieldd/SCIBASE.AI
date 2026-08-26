# AI-Powered Research Assistant Suite

A self-contained toolkit that augments scientific workflows with an embedded
analyst, reviewer, and strategist. The suite is dependency-free (Python
standard library only) and ships with a full pytest suite.

## Capabilities

### 1. Auto Peer Review Reports — `scibase.review`

Analyzes a manuscript and generates structured, category-based review
suggestions:

- **Clarity and coherence** checks (jargon, vague wording, sentence length)
- **Statistical red flags** (unreported p-values, sample sizes, correlations)
- **Methodological red flags** (e.g. missing survey response rates)
- **Missing citations** and scope misalignment
- **Claims vs. evidence alignment** (unsupported or thinly-evidenced claims)

Templates are adaptable per domain (`molecular-biology`, `quantum-physics`,
`clinical-trials`); unknown domains fall back to a generic template. Each
review produces a 0-100 score.

```python
from scibase import Manuscript, generate_peer_review

ms = Manuscript(
    title="My study",
    abstract="A significant p-value was observed.",
    claims=[("The treatment works.", None)],
    citations=["Smith et al., 2021"],
    domain="clinical-trials",
)
report = generate_peer_review(ms)
print(report.summary)
print(report.score)   # 0-100
for issue in report.issues:
    print(issue.category, issue.severity, issue.message, issue.suggestion)
```

### 2. Reproducibility Checker — `scibase.reproducibility`

Inspects a project directory and verifies:

- **Pipeline presence** — source/notebook files exist
- **Raw data present** — data files under `data/`
- **Tests present** — `test_*` files
- **Output consistency** — reported results match actual file contents
- **Dependency/version integrity** — every dependency is pinned
- **Determinism** — byte-identical outputs across `reproducibility/runs/`

Each check contributes a reproducibility confidence score from 0.0 to 1.0.

```python
from pathlib import Path
from scibase import Project, ReproducibilityChecker

project = Project(
    name="example",
    root=Path("my_research"),
    reported_results={"results.txt": "accuracy=0.94"},
    dependencies={"numpy": "1.26.4", "pandas": None},  # None => unpinned
)
report = ReproducibilityChecker().check(project)
print(report.score, report.reproducible)
for issue in report.issues:
    print(issue.code, issue.message)
```

### 3. Research Gap Finder — `scibase.gap_finder`

Scans a corpus of papers and identifies:

- **Under-studied intersections** — topic combinations where each topic is
  individually active but the combination rarely (or never) co-occurs
- **Frequently cited unresolved questions** — extracted from limitations
  sections, ranked by citation count
- A personalized **research opportunities feed** ranked against the user's
  interests and project history

```python
from scibase import GapFinder, Paper

papers = [
    Paper(id="p1", title="...", topics=["CRISPR", "Alzheimer's"], citations=40,
          open_questions=["The role of glia remains unclear."]),
    # ...
]
finder = GapFinder(papers)
for opp in finder.under_studied_intersections():
    print(opp.topics, opp.rationale, opp.score)

for question, papers, citations in finder.unresolved_questions():
    print(question, papers, citations)

feed = finder.research_opportunities_feed(
    interests=["single-cell RNA-seq"], project_history=["CRISPR"])
```

## Running the tests

```bash
python -m pytest tests/ -q
```