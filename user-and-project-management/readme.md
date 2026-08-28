# User & Project Management

User and project management is the identity, access, and workspace governance
layer of SCIBASE. It determines who researchers are, how they authenticate,
what their public reputation looks like, and who can see, edit, and govern a
research project. Every repository ([Project Repository & Version
Control](../project-repository-version-control/readme.md)) belongs to exactly
one user or organization and inherits its permissions from the project space.

This document covers four layers: authentication & identity, researcher
profiles, project spaces, and permissions & access control.

---

## 1. Authentication & Identity

### 1.1 Email & password with 2FA

Every account can be created with an email and password. Two-factor
authentication (TOTP-based authenticator app, with SMS backup codes) is
available on every account and can be made mandatory by an organization owner
or institution admin. Passwords are stored using a slow password hash
(Argon2id). 2FA recovery codes are generated at enrollment and must be saved by
the user.

```console
$ scibase signup --email dan@ualberta.ca
$ scibase login --email dan@ualberta.ca --2fa
Verification code: 123456
$ scibase 2fa enable
```

### 1.2 OAuth integrations

ORCID, Google, GitHub, and LinkedIn can be used as login providers or linked to
an existing account. ORCID is treated as the primary scholarly identity; the
others are convenience providers.

```console
$ scibase login --provider orcid
$ scibase login --provider github
$ scibase link-provider linkedin
$ scibase auth unlink --provider linkedin
```

### 1.3 Institutional login via SAML

Universities and research centers can enable SAML single sign-on for their
whole domain. A domain can be claimed by an institution, after which members
authenticate against the institution's IdP, which also asserts their
affiliation automatically. Any user with a verified institutional email (e.g.
`@ualberta.ca`) can log in through the institution's IdP.

```console
$ scibase login --provider saml --domain ualberta.ca
```

### 1.4 Account linking & unified identity

Multiple providers can be linked to one account, producing one unified
identity. Regardless of the login path, a user resolves to a single stable
account ID, so forks, endorsements, and metrics are never split across
provider identities. Signing in with any linked provider reaches the same
profile, projects, and permissions.

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

### 1.5 Anonymous mode

Open peer review and public browsing can be done anonymously. Anonymous users
get a stable pseudonymous handle (e.g. `anonymous-reviewer-7k2p`) that can
accrue review credit without exposing identity; their actions are excluded from
attribution on the reviewed work.

```console
$ scibase login --anonymous
```

---

## 2. Researcher Profiles

Every user has a public profile that doubles as their attribution record.

### 2.1 ORCID sync

A user can connect their ORCID iD to pull in publication history, affiliations,
and grants. Synced records appear on the profile as verified, read-only entries
and update on a user-configurable schedule; the user can hide individual
entries without unlinking ORCID.

```console
$ scibase orcid sync
```

### 2.2 Profile elements

Every profile exposes: name, institution, field, bio, keywords, and photo. The
public profile is rendered from a canonical endpoint:

```text
https://scibase.ai/users/danwusu
```

```json
{
  "handle": "danwusu",
  "name": "Daniel Wusu",
  "orcid": "0000-0000-0000-0000",
  "institution": "University of Alberta",
  "field": "Electrical & Computer Engineering",
  "bio": "ML infrastructure and reproducible science.",
  "keywords": ["machine learning", "reproducibility", "single-cell"],
  "photo": "https://scibase.ai/users/danwusu/avatar.png"
}
```

### 2.3 Activity feed

Each profile has an activity feed of recent projects, peer reviews, and
collaborations — created, forked, or merged repositories, published versions,
completed reviews, and new collaborations, in reverse chronological order.

### 2.4 Citation & reputation metrics

Profiles aggregate public metrics: downloads, forks, endorsements, and a
reproducibility score. Endorsements are verifiable attestations from other
users. The reproducibility score comes from the reproducibility checks described
in [Project Repository & Version
Control](../project-repository-version-control/readme.md) (pipeline presence,
determinism, pinned dependencies).

```json
{
  "metrics": {
    "downloads": 482,
    "forks": 37,
    "endorsements": 12,
    "reproducibility_score": 0.93
  }
}
```

### 2.5 Public vs private profiles

Profile mode is user-controlled:

- **Public** — profile page, metrics, and activity feed are visible to everyone.
- **Private** — profile is only visible to signed-in collaborators; metrics are
  hidden; the public page returns 404. Authorship on public repositories is
  still attributed unless anonymous mode is active.

```console
$ scibase profile set bio "Single-cell genomics and reproducible pipelines."
$ scibase profile set keywords "single-cell,rna-seq"
$ scibase profile set visibility private
```

---

## 3. Project Spaces (Scientific Workspaces)

A **project space** is the container around a research effort. It bundles
documents, code, datasets, and discussion threads, and links collaborators,
funding sources, and institutions. A space wraps one or more repositories
([Project Repository & Version
Control](../project-repository-version-control/readme.md)). Unlike a published
repository, a space is a living container: it can hold draft documents,
discussion, and mixed-access collaborators before anything is released.

### 3.1 Space contents

- **Documents** — manuscripts and notes, authored natively in Markdown, LaTeX,
  or Jupyter notebooks.
- **Code and datasets** — analysis scripts and data files under the repository
  layout (`code/`, `data/`, `notebooks/`), versioned and reproducible.
- **Discussion threads & comments** — inline comments on documents and code and
  threaded discussions per space.
- **Metadata & citations** — project title, description, tags, funding, and
  linked institutions, reusing the same `metadata.json` shape as repositories.
- **Linked collaborators, funding sources, and institutions** — people, grants,
  and organizations tied to the space for attribution and reporting.

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

### 3.2 Authoring

Spaces are Markdown/LaTeX/Jupyter-native. Documents and notebooks are edited
in-browser and versioned exactly like repository files.

### 3.3 Lifecycle

Spaces can be created, managed, and archived. Archiving freezes content,
revokes write access for non-owners, and moves the space to read-only; archived
spaces can be restored by an owner or admin, and can later be published as a
repository with a DOI.

```console
$ scibase space create "Single-cell atlas of the mouse liver" \
    --repo single-cell-atlas-of-mouse-liver --visibility private
$ scibase space add-document mouse-liver-atlas manuscript/draft.md
$ scibase space discuss mouse-liver-atlas "proposal: drop low-count cells"
$ scibase space metadata set --funding "NSERC RGPIN-2024-0000"
$ scibase space archive mouse-liver-atlas
```

---

## 4. Permissions & Access Control

### 4.1 Visibility settings

Every space is one of:

- **Public** — visible and browsable by anyone; published repositories get DOIs.
- **Private** — visible only to invited members.
- **Institutional-only** — visible to any authenticated member of a linked
  institution (SAML domain).
- **Invitation-only** — visible only to explicitly invited accounts; strongest
  default for in-progress work.

```console
$ scibase space visibility set institutional-only
```

### 4.2 Roles

Membership is role-based. Roles are hierarchical — a role inherits all
permissions of the roles below it:

| Role        | Capabilities |
|-------------|--------------|
| **Owner**   | Everything; transfers ownership, archives/deletes the space, changes visibility. |
| **Admin**   | Everything except ownership transfer and deletion; manages members and roles. |
| **Contributor** | Read, write documents/code/datasets, open and merge merge requests. |
| **Reviewer**    | Read everything, comment and review; cannot push to protected branches. |
| **Viewer**      | Read-only access to all objects. |

```console
$ scibase space member add aisha@ualberta.ca --role reviewer
$ scibase space member role set aisha@ualberta.ca contributor
```

### 4.3 Custom sharing with external collaborators

External collaborators (no institutional affiliation) can be invited with
time-limited or read-only access. Invitations carry an expiry and an optional
capability cap; expired shares are automatically revoked.

```console
$ scibase space share invite external@lab.org --read-only --expires 2026-12-31
$ scibase space share mouse-liver-atlas --role reviewer --read-only
```

### 4.4 Fine-grained object-level control

Access is enforceable per object, not just per role. Permissions are inherited
from the role default and narrowed by explicit object ACLs; an explicit ACL
always overrides the role default. For example, a reviewer may be allowed to
comment on code but denied dataset downloads, or a contributor may edit code
while dataset access stays restricted:

```console
$ scibase object acl set data/ --deny download --grant comment
$ scibase object acl set code/ --grant edit
```

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

### 4.5 Audit log

Every space keeps an immutable, project-level audit log recording access
history and changes by user: who viewed, edited, downloaded, changed roles, or
modified visibility, with timestamps and the repository commit when applicable.
Audit records are append-only and cannot be edited or deleted by members.

```console
$ scibase space audit
2026-08-28T10:02:11Z  danwusu       changed visibility to institutional-only
2026-08-28T10:01:57Z  aisha@ualberta.ca  added as reviewer
2026-08-27T16:40:00Z  external@lab.org   granted read-only access (expires 2026-12-31)
$ scibase space audit mouse-liver-atlas --user ava-chen
```

```json
{
  "entries": [
    {"at": "2026-08-26T14:02:11Z", "user": "danwusu", "action": "edit", "object": "code/normalize.py"},
    {"at": "2026-08-26T15:40:55Z", "user": "ava-chen", "action": "download", "object": "data/matrix.csv"},
    {"at": "2026-08-27T09:12:00Z", "user": "danwusu", "action": "role.set", "object": "ava-chen", "detail": "viewer -> contributor"}
  ]
}
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

Granular identity, access control, and governance let researchers get credit
for their work while institutions keep visibility and compliance. Verified
identity and transparent permissions underpin trustworthy collaboration,
meaningful attribution, and the reproducibility guarantees that make SCIBASE a
credible home for open science.