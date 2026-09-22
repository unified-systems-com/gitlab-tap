# TAP GitLab Plugin Specification

**GitLab as grid vocabulary: v0 carries one outer node, the GitLab instance (a self-managed server or gitlab.com), so a design can place it before anything is collected.**

## Plugin Identity

| Field | Value |
| --- | --- |
| Slug | `gitlab` |
| Display name | TAP GitLab |
| Description | GitLab as grid vocabulary: v0 carries one outer node, the GitLab instance (a self-managed server or gitlab.com), so a design can place it before anything is collected. |
| Kind | Leaf plugin: GitLab vocabulary. Consumes nothing in v0; consumed by instance plugins that place it in a design (highbar first). |

**Default dimensions**

| Dimension | Value | Why |
| --- | --- | --- |
| (none) | | `gitlab__gitlab_instance` declares no default dimension in v0. The only candidate is the `dcom` axis, and its value is a property of the observation, not the type: a seeded design node is `design`, the same type observed by a future collector is `configuration`. The seeding bundle stamps it per node. |

## Philosophy

This is a thin v0 (ruled 2026-09-22 for the highbar starter set): it exists to put the piece on the board so a design can reference it, not to model the domain. The full `create-plugin-spec` interview, prior-art search and requirement buy-in run when this plugin grows past v0; nothing here pre-empts them.

The one type, `gitlab__gitlab_instance`, is the outermost thing a reader of a diagram recognises for GitLab. Everything inside it (users, groups, policies, projects, sessions) is later vocabulary, added when something observes or designs it.

Three states hold for every observed field: blank means *not observed*, never *empty*. A design-phase node carries only its name; its identifiers stay blank until a collector reads them.

**Provenance markers:** every node of this type seeded in v0 is *designed* (stamped `dcom: design` by the bundle that seeds it). No field is *observed* until the collector (`req-gitlab-collector`, Backlog) exists.

## Goals

| # | Name | Description |
| --- | --- | --- |
| 1 | On The Board | Exist as an installable plugin so the highbar stack can boot with it. |
| 2 | Designable | Let a design place the GitLab outer node before any access exists. |

## Requirements

| RID | Name | Status | Notes |
| --- | --- | --- | --- |
| req-gitlab-model | [GitLab Instance Model](#gitlab-instance-model) | Implemented | The one outer node: its fields, natural key, icon and display |
| req-gitlab-record | [CI Record and Tests](#ci-record-and-tests) | Implemented | The in-package `ci` boot record and the manifest/behaviour tests |
| req-gitlab-collector | [Collector](#collector) | Backlog | Observe real GitLab state onto the grid; deferred until access exists |

---

### GitLab Instance Model
----
RID: `req-gitlab-model`

Status: `Implemented`

A GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines.

#### Implementation

`tap_plugin/gitlab/models/gitlab_instance.py` defines `GitlabInstance(BaseModel)` with `ENTITY_TYPE = "gitlab__gitlab_instance"`, `ENTITY_ICON = "gitlab-instance"` (SVG at `static/gitlab/icons/gitlab-instance.svg`), no default dimensions, and fields `name` (required), `base_url` (The instance's base URL, for example https://gitlab.example.com. Blank until observed.), `configuration` (object) and `tags` (object). `NATURAL_KEY = ("name",)`: a design-phase node has no observed identifier, so its name is the only fact it carries; the key is revisited when `req-gitlab-collector` makes `base_url` observable.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-model-1 | Created Through The Service Layer | Implemented | A `create_node` write with only `name` succeeds and the row carries it. | |
| req-gitlab-model-2 | Name Required | Implemented | A `create_node` write without `name` is refused. | |
| req-gitlab-model-3 | Keyed By Name | Implemented | `NATURAL_KEY` is `("name",)` and every key field is a model field. | |

---

### CI Record and Tests
----
RID: `req-gitlab-record`

Status: `Implemented`

The in-package `ci` boot record (`req-boot-bootstrap-ci-record`) and the tests that run in it.

#### Implementation

`tap_plugin/gitlab/boot/ci.boot.json` installs this plugin alone (it declares no dependencies), offline and credential-free; the consumer flips self to editable. `tap_plugin/gitlab/tests/test_gitlab_manifest.py` runs `validate_plugin` at structure and strict levels; `tests/test_gitlab_instance.py` covers `req-gitlab-model`.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-record-1 | Record Declared | Implemented | The manifest declares the `ci` record with its sha256. | |
| req-gitlab-record-2 | Validates Strict | Implemented | `validate_plugin --strict` passes on the package. | |

---

### Collector
----
RID: `req-gitlab-collector`

Status: `Backlog`

Observe real GitLab state onto the grid; deferred until access exists.

## Model catalog

| Model | Entity type | Category | Rationale |
| --- | --- | --- | --- |
| `GitlabInstance` | `gitlab__gitlab_instance` | Outer node | The one node a reader recognises as GitLab; everything else nests inside it later. |

## Icons

`gitlab-instance` is GitLab's own mark, used nominatively to identify the vendor on diagrams. The mark remains its owner's trademark; it is not covered by this repository's licence.
