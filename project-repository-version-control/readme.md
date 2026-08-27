# Project Repository & Version Control

A **project repository** is the atomic unit of collaboration, publication, and
reproducibility on SCIBASE. It behaves like a hybrid of a GitHub repository, a
Jupyter workspace, and a scientific preprint: one structured container that
holds everything a research effort produces — manuscripts, data, code, models,
protocols, results, and metadata.

Each repository is an independent, git-backed unit. Repositories can be private
(draft), shared with collaborators, or published (citable, with a DOI).

---

## 1. Repository Structure & Components

A repository always exposes the following canonical layout:

```
<repository-name>/
├── manuscript/            # Structured text: Markdown, LaTeX, or WYSIWYG
├── data/                  # Uploaded datasets, structured tables, or linked APIs
├── code/                  # Analysis scripts, notebooks, packages
├── notebooks/             # Jupyter-style interactive documents
├── results/               # Plots, figures, models, or trained weights
├── protocols/             # Editable experiment plans and lab procedures
└── metadata.json          # DOI, authors, affiliations, funding, tags, schema.org
```

Top-level directories are optional; a repository must contain at least a
`metadata.json` to be created. Any directory may be added later. Ad-hoc files
at the repository root (e.g. a top-level `README.md` or `run_analysis.py`) are
allowed and versioned like everything else.

### `metadata.json`

The single source of truth for repository-level metadata:

```json
{
  "name": "single-cell-atlas-of-mouse-liver",
  "title": "A single-cell atlas of the mouse liver",
  "doi": "10.5555/scibase.0000001",
  "version": "1.0.0",
  "tags": ["single-cell", "rna-seq", "liver"],
  "authors": [
    {"name": "Daniel Wusu", "orcid": "0000-0000-0000-0000", "affiliation": "UAlberta EE"}
  ],
  "affiliations": ["University of Alberta"],
  "funding": [{"funder": "NSERC", "grant": "RGPIN-2024-0000"}],
  "schema.org": {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "license": "CC-BY-4.0"
  }
}
```

The `metadata.json` also encodes schema.org markup so published repositories
are indexable by search engines and scholarly aggregators.

Forks additionally record their parent repository via `derived_from`, preserving
attribution for downstream derivations (see [§3](#3-collaboration--forking)):

```json
"derived_from": "https://scibase.ai/repos/danwusu/mouse-liver-atlas"
```

---

## 2. File & Metadata Versioning

- **Full version control** for every artifact — documents, datasets, and code —
  with commit history, rollback, and tag support.
- **Git-native backend.** Each repository is a real git repository. Large files
  (datasets, trained weights) are stored via Git LFS so history stays lean.
- **Semantic versioning.** Released versions follow `MAJOR.MINOR.PATCH`
  (e.g. `v1.0.0`, `v2.1.0`). Pre-release and preprint tags such as
  `preprint-v2.1` or `preprint-v1.0-rc1` are supported; shortened `MAJOR.MINOR`
  forms (e.g. `v1.0`) are accepted as aliases for the latest patch.
- **Hash-based integrity.** Every blob is content-addressed (SHA-256). The tree
  hash of a tagged commit is recorded alongside the tag, giving a
  cryptographically verifiable fingerprint for reproducibility and citation.

### Commit workflow

```console
$ scibase commit -m "add normalized expression matrix"
$ scibase tag -v v1.0.0
$ scibase rollback v0.9.0
```

---

## 3. Collaboration & Forking

- **Forking.** Any user can fork a published repository. Forks record their
  parent repository in `metadata.json` (`derived_from`), preserving attribution
  for downstream derivations.
- **Merge Requests (MRs).** Collaborators propose changes as MRs with discussion
  threads, inline review comments, approvals, and a merge action.
- **Branching.** Parallel experiments or competing hypotheses live on branches;
  branches can be compared and merged via MRs.
- **Provenance tracking.** Every commit records author, timestamp, and the
  files changed, so "who contributed what, and when" is always recoverable.

---

## 4. In-Browser Editors & Diffs

- **Inline editors** for Markdown, LaTeX, CSV, JSON, and `.ipynb` notebooks.
- **Code-aware diffing** for Python, R, Julia, and other common languages.
- **Rich data diffs** for tables and structured datasets — row/column-level
  change highlighting rather than raw text.
- **Visual revision timeline** for comparing versions and rolling back.

---

## 5. Computation-Aware Reproducibility

- **Auto-executed reproducibility pipelines.** Any repository can declare an
  entrypoint (e.g. `run_analysis.ipynb` in `notebooks/` or `code/`). Executing
  it from raw `data/` should regenerate `results/`.
- **Container support.** Repositories may ship a `Dockerfile` or `environment.yml`
  (Conda) to pin the execution environment.
- **Raw data → code → outputs.** The platform verifies that outputs can be
  reproduced from the committed raw data and committed code alone.
- **Execution sandboxes.** Pipelines run in isolated sandboxes for secure
  runtime validation.

---

## 6. Repository Identifiers & Citation

- **DOIs.** A DOI is minted per repository and per tagged version via Crossref
  or DataCite.
- **Auto-generated citations** in APA, MLA, and BibTeX formats from
  `metadata.json`. Given the example metadata in [§1](#1-repository-structure--components):

  ```text
  APA:    Wusu, D. (2026). A single-cell atlas of the mouse liver (Version 1.0.0)
          [Data set]. SCIBASE. https://doi.org/10.5555/scibase.0000001
  MLA:    Wusu, Daniel. "A Single-Cell Atlas of the Mouse Liver." SCIBASE, Version 1.0.0,
          doi:10.5555/scibase.0000001.
  BibTeX: @misc{wusu2026single,
            author    = {Wusu, Daniel},
            title     = {A single-cell atlas of the mouse liver},
            year      = {2026},
            publisher = {SCIBASE},
            version   = {1.0.0},
            doi       = {10.5555/scibase.0000001}
          }
  ```

- **“Cite this project” badge** showing dynamic metadata and usage metrics
  (views, downloads, citations).

---

## 7. Programmatic Access & Export

- **Public REST API** for project and data access:
  - `GET /repos/{owner}/{name}` — repository metadata
  - `GET /repos/{owner}/{name}/tree` — file listing
  - `GET /repos/{owner}/{name}/blob/{path}` — file contents
  - `POST /repos` — create a repository
  - `PUT /repos/{owner}/{name}/blob/{path}` — write a file
- **Export bundles.** Any repository (or tagged version) can be exported as a
  zipped package containing a manifest, full file tree, and `metadata.json`.
  The manifest records the repository identity, tagged version, tree hash, and
  every file with its SHA-256 so a bundle is self-verifying:

  ```json
  {
    "schema_version": "1",
    "repository": "danwusu/mouse-liver-atlas",
    "version": "1.0.0",
    "tree_sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "exported_at": "2026-08-26T00:00:00Z",
    "files": [
      {"path": "metadata.json", "sha256": "…", "size": 1234},
      {"path": "data/matrix.csv", "sha256": "…", "size": 48291}
    ]
  }
  ```

- **Git-compatible CLI** (`scibase` as shown above) for advanced contributors
  and labs that prefer working from the terminal.

---

## Optional Advanced Features (Post-MVP)

- **Provenance tree visualization** — interactive graph of forks, merges, and
  citations.
- **Immutable snapshots** published to IPFS (or an append-only ledger) for
  long-term archival integrity.
- **Notebook diff viewer** with output/version playback.

---

## Why This Matters

Reproducibility, transparency, and collaboration are mission-critical. A robust
project repository system with integrated version control underpins the
platform's credibility, researcher trust, and long-term archival integrity.