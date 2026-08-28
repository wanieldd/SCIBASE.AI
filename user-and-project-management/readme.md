# User & Project Management

User and project management is the foundation of collaboration, access control,
and attribution on SCIBASE. It provides identity, researcher profiles, and
scientific workspaces (project spaces) with granular permissions, so that
researchers, teams, institutions, and external partners can work together
securely while getting credit for their work.

Every repository ([Project Repository & Version
Control](../project-repository-version-control/readme.md)) belongs to exactly
one user or organization and inherits its permissions from the project space.

---

## 1. Authentication & Identity

### Sign-in methods

- **Email & password** with optional two-factor authentication (TOTP-based
  authenticator app or SMS backup codes).
- **OAuth integrations** for ORCID, Google, GitHub, and LinkedIn. ORCID is
  treated as the primary scholarly identity; the others are convenience
  providers.
- **Institutional login via SAML** for universities and research centers. A
  domain can be claimed by an institution, after which members authenticate
  against the institution's IdP.
- **Account linking.** Multiple providers can be attached to a single account,
  producing one unified identity. Signing in with any linked provider reaches
  the same profile, projects, and permissions.
- **Anonymous user mode.** Opt-in anonymous browsing and open peer review.
  Anonymous reviewers get a stable pseudonymous handle (e.g.
  `anonymous-reviewer-7k2p`) that can accrue review credit without exposing
  identity.

### Account identity

```json
{
  "username": "danwusu",
  "email": "dan@ualberta.ca",
  "providers": ["email", "orcid", "github"],
  "orcid": "0000-0000-0000-0000",
  "institution": "University of Alberta",
  "saml_domain": "ualberta.ca",
  "two_factor_enabled": true,
  "anonymous_mode": false
}
```

### CLI

```console
$ scibase login --provider orcid
$ scibase login --provider saml --domain ualberta.ca
$ scibase 2fa enable
$ scibase link-provider github
$ scibase whoami
```

---

## 2. Researcher Profiles

Every user has a public profile that doubles as their attribution record.

### Profile elements

- Name, institution, field, short bio, and photo.
- **ORCID sync.** Pulls in publication history, affiliations, and grants;
  synced records appear on the profile as verified entries.
- **Keywords** describing research interests, used to route opportunities and
  recommendations.
- **Activity feed.** Recent projects, peer reviews, and collaborations, in
  reverse chronological order.
- **Citation & reputation metrics:** downloads, forks, endorsements, and a
  reproducibility score derived from the reproducibility checks of the user's
  published repositories (see [Project Repository & Version
  Control](../project-repository-version-control/readme.md)).
- **Public vs private profile modes.** Private profiles hide the profile page
  (but still attribute authorship on public repositories unless anonymous
  mode is active).

### Profile record

```json
{
  "username": "danwusu",
  "name": "Daniel Wusu",
  "institution": "University of Alberta",
  "field": "Computational Biology",
  "bio": "Single-cell genomics and reproducible pipelines.",
  "photo": "https://scibase.ai/users/danwusu/photo",
  "keywords": ["single-cell", "rna-seq", "reproducibility"],
  "orcid": "0000-0000-0000-0000",
  "metrics": {
    "downloads": 482,
    "forks": 37,
    "endorsements": 12,
    "reproducibility_score": 0.93
  },
  "visibility": "public"
}
```

### CLI

```console
$ scibase profile set bio "Single-cell genomics and reproducible pipelines."
$ scibase profile set keywords "single-cell,rna-seq"
$ scibase orcid sync
$ scibase profile set visibility private
```

---

## 3. Project Spaces (Scientific Workspaces)

A **project space** is a collaborative workspace that groups everything a
research effort produces. Unlike a published repository (see Project Repository
& Version Control), a space is a living container: it can hold draft documents,
discussion, and mixed-access collaborators before anything is released.

Each space contains:

- **Documents** — manuscripts and notes, authored natively in Markdown, LaTeX,
  or Jupyter notebooks.
- **Code and datasets** — analysis scripts and data files, versioned and
  reproducible like repository artifacts.
- **Discussion threads and comments** — inline comments on documents and
  threaded discussions per space.
- **Project metadata and citations** — reuse the same `metadata.json` shape as
  repositories, extended with collaborators, funding sources, and institutions.
- **Linked collaborators, funding sources, and institutions** — people, grants,
  and organizations tied to the space for attribution and reporting.

### Space metadata

```json
{
  "name": "mouse-liver-atlas",
  "title": "A single-cell atlas of the mouse liver",
  "collaborators": [
    {"name": "Daniel Wusu", "orcid": "0000-0000-0000-0000", "role": "owner"},
    {"name": "Ava Chen", "orcid": "0000-0000-0000-0001", "role": "contributor"}
  ],
  "funding": [{"funder": "NSERC", "grant": "RGPIN-2024-0000"}],
  "institutions": ["University of Alberta"],
  "visibility": "private"
}
```

### Space lifecycle

- **Create** — instantiate a space with a name and initial visibility.
- **Manage** — add collaborators, files, discussions, and metadata over time.
- **Archive** — freeze a finished space into read-only state while keeping it
  browsable; archived spaces can later be published as a repository with a DOI.

### CLI

```console
$ scibase space create mouse-liver-atlas --visibility private
$ scibase space add-document mouse-liver-atlas manuscript/draft.md
$ scibase space discuss mouse-liver-atlas "proposal: drop low-count cells"
$ scibase space archive mouse-liver-atlas
```

---

## 4. Permissions & Access Control

### Visibility settings

Each space and repository has one visibility level:

- **Public** — visible to everyone, indexable, citable.
- **Private** — visible only to members.
- **Institutional-only** — visible to any authenticated member of the linked
  institution (SAML domain).
- **Invitation-only** — visible only to explicitly invited accounts.

### Role-based access

Members are assigned one of five roles. Roles are hierarchical: a role
inherits all permissions of the roles below it.

| Role        | Permissions                                                                 |
|-------------|-----------------------------------------------------------------------------|
| **Owner**   | Full control, including deletion, ownership transfer, and role assignment    |
| **Admin**   | Manage members, roles, settings, and the audit log                           |
| **Contributor** | Edit documents, code, and data; open and merge MRs                       |
| **Reviewer**    | View and comment on all content; approve or request changes on MRs      |
| **Viewer**      | Read-only access to the space                                              |

### Custom sharing

- **External collaborators** can be invited with time-limited or read-only
  access, even without an institutional account.
- Invitations carry an expiry and an optional capability cap.

```console
$ scibase space invite mouse-liver-atlas ada@stanford.edu --role viewer --expires 2026-12-31
$ scibase space role set mouse-liver-atlas danwusu admin
$ scibase space share mouse-liver-atlas --role reviewer --read-only
```

### Fine-grained object-level control

Permissions can be narrowed below the role level on individual objects:

- Allow code editing but restrict data downloads (e.g. Contributor may edit
  `code/` but only view `data/`).
- Allow reviewers to read manuscripts but not datasets.

```json
{
  "subject": "danwusu",
  "role": "contributor",
  "restrictions": {
    "code": "edit",
    "data": "view",
    "notebooks": "edit"
  }
}
```

### Project-level audit log

Every space keeps an immutable audit log recording access history and changes
by user: logins, file edits, permission changes, and export/download events.

```json
{
  "entries": [
    {"at": "2026-08-26T14:02:11Z", "user": "danwusu", "action": "edit", "object": "code/normalize.py"},
    {"at": "2026-08-26T15:40:55Z", "user": "ava-chen", "action": "download", "object": "data/matrix.csv"},
    {"at": "2026-08-27T09:12:00Z", "user": "danwusu", "action": "role.set", "object": "ava-chen", "detail": "viewer -> contributor"}
  ]
}
```

```console
$ scibase space audit mouse-liver-atlas
$ scibase space audit mouse-liver-atlas --user ava-chen
```

---

## Optional Advanced Features (Post-MVP)

- **Single sign-on federation** — SAML discovery and cross-institution trust
  lists so researchers at partner universities are auto-provisioned.
- **Delegated administration** — org-level admins who govern many spaces and
  members at once.
- **Reputation-based review queues** — route peer reviews to the highest
  reproducibility-scored reviewers in a field.

---

## Why This Matters

Granular identity, access control, and attribution are what let researchers get
credit for their work while institutions maintain visibility and compliance.
By integrating identity verification (ORCID, SAML), reputation incentives, and
fine-grained governance, this layer makes large-scale scientific collaboration
trustworthy and auditable.