# Scientific Knowledge Graph

The **Scientific Knowledge Graph** turns unstructured research into a
structured, interconnected graph of entities and relationships. Every uploaded
artifact — papers, datasets, notebooks, protocols — is parsed into typed
entities (concepts, authors, tools, datasets, protocols, funders) and linked
by their real-world relationships. Surfacing those connections through
intuitive navigation and AI-driven recommendations makes the platform more than
a repository: it becomes a living map of global scientific knowledge.

The graph builds directly on the metadata authored in [Project Repository &
Version Control](../project-repository-version-control/readme.md) and the
identity layer in [User & Project
Management](../user-and-project-management/readme.md). It operates in three
layers: entity extraction, knowledge navigation, and AI research
recommendations.

---

## 1. Entity Extraction

Every uploaded or published repository is automatically parsed to populate the
graph.

### 1.1 What gets extracted

- **Concepts** — gene names, materials, diseases, algorithms, and other
  domain terms mentioned in text.
- **Authors and affiliations** — people and their institutions, resolved to
  their researcher profiles ([User & Project
  Management](../user-and-project-management/readme.md)).
- **Tools, instruments, and software libraries** — analysis tools, hardware,
  and code dependencies referenced by the work.
- **Cited references and DOIs** — the bibliography, deduplicated and resolved
  to canonical identifiers.
- **Ontology terms** — named entities normalized against public ontologies
  such as MeSH, UniProt, and PubChem, so "Alzheimer's" and "Alzheimer's
  disease" resolve to the same node.

### 1.2 How extraction works

- **NLP models fine-tuned on scientific corpora** (PubMed, arXiv, Crossref)
  run over manuscript text, notebook outputs, and protocol descriptions.
- Extracted entities are resolved and deduplicated against canonical
  identifiers (ORCID for people, DOIs for papers, ontology accession IDs for
  concepts).
- **Linked data output.** The graph exposes entities and relationships as
  linked data with schema.org-compatible metadata, reusing the schema.org
  block already produced by `metadata.json` in each repository.

```json
{
  "@context": "https://schema.org",
  "@type": "ScholarlyArticle",
  "identifier": "10.5555/scibase.0000001",
  "author": [{"@type": "Person", "identifier": "https://orcid.org/0000-0000-0000-0000"}],
  "mentions": [
    {"@type": "DefinedTerm", "name": "CRISPR", "identifier": "mesh:D047571"},
    {"@type": "SoftwareApplication", "name": "scanpy", "identifier": "bio.tools:scanpy"}
  ],
  "citation": ["10.1038/s41586-018-0257-6"]
}
```

### 1.3 Entity pages

Each entity gets a canonical page aggregating everything the graph knows about
it:

- **Aggregated data** — the count of projects, papers, datasets, and protocols
  that reference it, plus its ontology definition when available.
- **Citations and usage contexts** — every context in which the entity was
  mentioned, linked back to the source repository and version.
- **Relationship list** — the typed edges connecting it to other entities
  (co-authors, derived-from datasets, methods using a tool).

```text
https://scibase.ai/graph/entities/concept/crispr
https://scibase.ai/graph/entities/person/orcid:0000-0000-0000-0000
https://scibase.ai/graph/entities/tool/scanpy
https://scibase.ai/graph/entities/dataset/mouse-liver-atlas
```

### 1.4 Use cases

- Index and structure millions of research objects for discoverability.
- Enable semantic search and cross-project inference.
- Build author graphs and lab-to-lab collaboration maps.

---

## 2. Knowledge Navigation

### 2.1 Interactive graph search UI

A graph-based explorer lets researchers ask relational questions and see the
answers as a navigable network:

- "Show all projects citing this dataset."
- "Visualize papers using this CRISPR protocol and clustering in
  neuroscience."
- "Find all experiments that reused this notebook."

The UI renders nodes and edges interactively — drag to explore, click a node
to open its entity page, and expand neighborhoods one hop at a time.

### 2.2 Dynamic node types

The graph supports heterogeneous node types, each with its own metadata:

| Node type   | Entity page | Example edge |
|-------------|-------------|--------------|
| **Authors** | Researcher profile | authored, co-authored, collaborates-with |
| **Concepts** | Ontology term | mentions, used-by |
| **Tools** | Software/library | requires, used-in |
| **Datasets** | Repository data | derived-from, cited-by |
| **Protocols** | Method document | used-by, requires |
| **Funders** | Grant/agency | funds, funds-project |

Edges are typed and directional, so queries like "which datasets cite this
protocol" are expressed directly over the graph rather than through keyword
search.

### 2.3 Filters

Result sets can be narrowed by:

- **Domain** — field or ontology branch (e.g. neuroscience, materials).
- **Institution** — author or funder affiliation.
- **Time** — publication or last-updated window.
- **Citation count** — influence thresholds.
- **Reproducibility** — only show artifacts with a passing reproducibility
  score (from the checks in [Project Repository & Version
  Control](../project-repository-version-control/readme.md)).

### 2.4 Exploratory research journeys

Navigation is designed for open-ended discovery paths — concept → dataset →
collaborators — rather than single-shot lookups. The interface tracks the
current exploration and suggests the next hop from the surrounding
neighborhood.

### 2.5 Use cases

- Discover related work you didn't know existed.
- Explore influence pathways of key datasets or methods.
- Identify knowledge gaps or underexplored intersections.

---

## 3. AI Research Recommendations

### 3.1 Recommendation engine

A personalized engine ranks entities and research objects for each user,
trained on:

- **User project activity** — repositories created, forked, viewed, and cited
  from their project spaces.
- **User citations and interests** — explicit keywords and implicit signals
  from extracted concepts.
- **Global research trends** — rising entity popularity and co-occurrence
  patterns across the whole graph.

### 3.2 Context-aware suggestions

Recommendations are phrased relative to the researcher's own work:

- "If you liked this paper, try this model or dataset."
- "Researchers in your field are citing this method."
- "This unresolved question connects to your last experiment."

Each suggestion links back to the underlying entities and to the other
researchers whose activity motivated it, so recommendations are auditable
rather than opaque.

### 3.3 Delivery surfaces

- **Sidebar in the project workspace** — inline suggestions while authoring,
  mapped to the current project's extracted concepts.
- **Weekly digest email** — a periodic summary of new entities, citations, and
  connections relevant to the user's interests.
- **"Discovery mode" UI** — a full-screen browsing surface for inspiration,
  showing trending intersections and unexpected connections.

### 3.4 Use cases

- Accelerate literature reviews and ideation.
- Spark interdisciplinary collaboration by surfacing adjacent fields.
- Help funders or institutions spot emerging research clusters.

---

## Optional Advanced Features (Post-MVP)

- **Real-time graph updates** — incremental re-indexing as repositories are
  edited rather than on publication only.
- **Community curation** — human review of uncertain extractions, with
  corrections feeding back into the extraction models.
- **Citation-prediction experiments** — forward-looking edges estimating which
  underexplored intersections are likely to gain momentum.
- **Federated graphs** — exchange subgraphs with external repositories via the
  linked-data export format.

---

## Why This Matters

As the volume of research explodes, finding what matters — and seeing how it
connects — becomes a core competitive advantage. The knowledge graph gives
researchers a sixth sense: the ability to visualize science as a living system,
find what others miss, and ask sharper questions. It turns scattered documents
into structured intelligence.