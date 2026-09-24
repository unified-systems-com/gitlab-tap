# TAP GitLab Plugin Specification

**GitLab as grid vocabulary: a small, self-managed GitLab as it is deployed — its components, Gitaly, runners, and what each runs on, stores to and trusts — and the objects inside it that a FedRAMP 20x operator governs, with a per-instance `/gitlab` page that draws the deployment and answers the operator's first questions.**

## Plugin Identity

| Field | Value |
| --- | --- |
| Slug | `gitlab` |
| Display name | TAP GitLab |
| Description | GitLab as grid vocabulary: a small self-managed GitLab as deployed (its components, Gitaly, runners and what they run on and store to) and the objects a FedRAMP operator governs in it (groups, projects, users, runners, protected branches and environments, CI/CD variables, keys and tokens, sign-in providers, audit streams), with a /gitlab page per instance. |
| Kind | Leaf plugin: GitLab vocabulary. Consumes `identity_core` (the OIDC issuer a sign-in provider trusts, and the human a user account is held by) and `aws_core` (the load-balancer edge its page's ingress search names) as vocabulary only; consumed by instance plugins that design or observe a GitLab (highbar first). |

**Default dimensions**

| Dimension | Value | Why |
| --- | --- | --- |
| `gitlab.plane` | `infrastructure` | On `gitlab__gitlab_component`, `gitlab__gitaly_node`, `gitlab__runner_manager` and the edges among processes and what they run on and store to: the processes a deployment runs. A property of the type, so a default. |
| `gitlab.plane` | `application` | On every other type and edge: the objects GitLab keeps in its own database (groups, projects, accounts, grants, credentials, sign-in, audit). |
| (none) | | `gitlab__gitlab_instance` carries no default dimension: it straddles both planes, and its `dcom` value belongs to the observation (a seeded design node is `design`, a collected one `configuration`), so the bundle that seeds a node stamps it. The same holds for `dcom` and `deployment.environment.*` on every type here. |

## Philosophy

This plugin models what a small, professional GitLab looks like when it is the core infrastructure shipping
service of a regulated estate — not an internet-facing behemoth. Its first deployment, ruled 2026-09-22, is
**all on AWS ECS (no EKS), from Chainguard FIPS container images, with GitLab Runner included**. The
vocabulary is not specific to that deployment: every edge that reaches the platform underneath leaves its
far end open, so the same types describe a GitLab on Kubernetes or on VMs.

Two planes, one vocabulary. The **infrastructure plane** is the deployment: the stateless components the
cloud-native split runs in containers (webservice/Puma, Workhorse, Sidekiq, GitLab Shell, the registry,
KAS, Pages, Mailroom, the exporter, the toolbox), the one stateful process (Gitaly), and the runner managers;
with what each runs on, which databases, Redis and object stores it reaches, which secrets it reads, and which
load balancers route to it. The **application plane** is what GitLab keeps in its database that an assessor
asks about: groups, projects and accounts; runner registrations and their scope; protected branches and
environments; CI/CD variables; deploy keys, deploy tokens and access tokens; sign-in providers; audit event
streams.

What this plugin deliberately does **not** model: the execution plane (pipelines, jobs, job logs, artifacts
as runs — Backlog, `req-gitlab-pipelines`); work tracking (issues, epics, merge requests as review objects —
`req-gitlab-nongoals`); neutral Git objects (commits, refs), which are `git_core`'s; gitlab.com's own SaaS
internals.

**Three states, never two.** Blank means *not observed*, never empty and never false. Every boolean is
nullable; every list is nullable (null is not observed, `[]` is observed-empty); every enum admits `""`
for not observed. The page's posture tiles read *not observed* when the grid holds none of a type for the
instance, never a reassuring zero, and the tables render a null boolean as `–`.

**Identity.** Every type except the instance is keyed first on `instance_name` — the owning instance's name,
which is the instance's own natural key — then on the fields a design can know (a name, a full path, a key).
The same group path on staging and production GitLab is two things. GitLab's numeric ids are carried as
nullable columns and are not keys yet; the keys are revisited when the collector (`req-gitlab-collector`)
observes those ids. `instance_name` repeats the instance's name on every row by design: identity must rest on
a column (`req-grid-entity-natural-key-10`), and the edges from the instance carry the relationship.

**The Gitaly support caveat.** GitLab supports only local storage for Gitaly repositories — "Alternatives such
as NFS or cloud-based file systems are not supported" (docs.gitlab.com/administration/gitaly, read
2026-09-22). EFS is therefore out, and so is a Fargate-hosted Gitaly with persistent repositories. The
reference deployment runs each Gitaly as an ECS service on the EC2 launch type with its own attached EBS
volume, modelled as `STORES_REPOSITORIES_ON_VOLUME` with `filesystem` recorded so an unsupported NFS/EFS
mount is visible. Running Gitaly in a container outside Kubernetes is itself outside GitLab's documented
configurations (Gitaly on Kubernetes is GA as of 18.11; ECS is not mentioned); the design owns that risk.

**Edition matters.** The Chainguard GitLab images are Community Edition (the `-ee` names do not resolve).
Several objects here exist only on paid tiers: protected environments (Premium), audit event streaming
(Ultimate), group-level protected branches (Premium). On a CE instance those tables read empty and the
audit-streaming tile reads *finding*: the audit log must leave another way (`audit_json.log` shipped by the
log driver), which this vocabulary does not yet model: aws_core's `WRITES_LOGS` does not accept an ECS service as its source.

**Prior art, and what it changed.** Cartography's GitLab module (nodes for organization, group, project,
branch, user, runner, CI variable, environment; roles as membership properties) set the names and the choice
of roles-as-properties. GitLabHound (BloodHound OpenGraph) contributed the edge lore — token-acts-as-user,
group invitations, per-branch push/merge grants. Neither models deploy keys, deploy tokens, protected
environments, audit streaming, the job-token allowlist or sign-in configuration: those are this corpus's
additions, driven by FedRAMP 20x questions and by incidents (OMGCICD's privileged-runner escape to a deploy
key; CVE-2023-7028 mitigated by SSO-only sign-in; CVE-2023-4812's Code Owner bypass). The full corpus —
node and edge justification, rejected candidates and the pinned source register — is
[corpus-gitlab.md](corpus-gitlab.md).

**Provenance markers.** *Documented*: every type, field and enum here is read from GitLab's documentation
and API reference (2026-09-22, via a summarising fetch; a collector build re-reads them verbatim). *Designed*:
the reference deployment below, and every node an instance plugin seeds from it (stamped `dcom: design`).
*Observed*: nothing yet — no field is observed until `req-gitlab-collector` exists; the page's tests observe
only the page's own behaviour against a fixture grid.

### The reference deployment

The small deployment this plugin's page and tests are shaped around (tests/fixtures/example-deployment.grift.json
is this, minus the EBS volume: aws_core requires an observed `volume_id` on create, which a design cannot know). All in one AWS account and VPC, private subnets,
ECS:

| Where it runs | GitLab process | Reaches |
| --- | --- | --- |
| ECS service `gitlab-webservice` (Fargate): two containers | `webservice` (Puma :8080), `workhorse` (:8181) | RDS PostgreSQL (`main`), ElastiCache Valkey (`all`), Gitaly (TLS), S3 buckets for artifacts, LFS, uploads, packages, Terraform state, CI secure files, dependency proxy; Secrets Manager |
| ECS service `gitlab-sidekiq` (Fargate) | `sidekiq` | the same database, Redis, Gitaly and buckets |
| ECS service `gitlab-shell` (Fargate) | `gitlab_shell` (gitlab-sshd :2222) | Gitaly |
| ECS service `gitlab-registry` (Fargate) | `registry` (:5000) | its own bucket; optionally the `registry` metadata database |
| ECS service `gitlab-toolbox` (Fargate, scheduled) | `toolbox` (migrations, backups) | the database; the backups bucket |
| ECS service `gitlab-gitaly` (**EC2 launch type**) | `gitaly-1` (standalone) | its attached **EBS volume** (ext4 or xfs) |
| ECS service `gitlab-runner-manager` (Fargate) | the runner manager (custom executor + Fargate driver) | the runner-cache bucket; launches each job as a task in a separate ECS cluster |

Ingress: an internal ALB (HTTPS 443 → Workhorse 8181, and the registry 5000; health check `/-/readiness`)
and an internal NLB (TCP 22 → gitlab-sshd 2222). Sign-in: OIDC (or SAML) to the organisation's IdP with
password sign-in disabled. Encryption: one KMS key for the buckets and secrets.

## Goals

| # | Name | Description |
| --- | --- | --- |
| 1 | Designable Deployment | A design can place a GitLab's components, Gitaly, runners and everything they run on and reach, before anything is built. |
| 2 | Governable Objects | The objects a FedRAMP 20x operator governs inside GitLab have types, with the posture fields an assessor asks about. |
| 3 | Honest Absence | Every observed fact has three states; nothing unobserved reads as clean. |
| 4 | One Page Per Instance | `/gitlab?instance=<name>` draws the deployment and answers the operator's first questions, for any instance on the grid. |
| 5 | Reusable Picture | The deployment layout is a module any page can use; it names no entity id. |

## Requirements

| RID | Name | Status | Notes |
| --- | --- | --- | --- |
| req-gitlab-model | [GitLab Instance Model](#gitlab-instance-model) | Implemented | The outer node, now with the instance-wide sign-in posture |
| req-gitlab-models-infrastructure | [Infrastructure Models](#infrastructure-models) | Implemented | Component, Gitaly node, runner manager |
| req-gitlab-models-application | [Application Models](#application-models) | Implemented | Twelve governed object types |
| req-gitlab-edges-infrastructure | [Infrastructure Edges](#infrastructure-edges) | Implemented | Processes, where they run, what they reach |
| req-gitlab-edges-application | [Application Edges](#application-edges) | Implemented | Hierarchy, membership, grants, credentials, sign-in, audit |
| req-gitlab-person-link | [Person Link](#person-link) | Implemented | A user account a person holds declares `HELD_BY_HUMAN__identity_core` to `identity_core__human` |
| req-gitlab-icons | [Icons](#icons-requirement) | Implemented | Own glyphs; GitLab's logo is not licensed for this use |
| req-gitlab-layout | [Deployment Layout](#deployment-layout) | Implemented | The reusable layout module |
| req-gitlab-panel-posture | [Posture Strip Panel](#posture-strip-panel) | Implemented | Instance chooser and posture tiles |
| req-gitlab-page | [GitLab Page](#gitlab-page) | Implemented | `/gitlab`: graph, posture, tables |
| req-gitlab-record | [CI Record and Tests](#ci-record-and-tests) | Implemented | The in-package `ci` record and the suite |
| req-gitlab-collector | [Collector](#collector) | Backlog | Observe a real GitLab onto the grid |
| req-gitlab-containment | [Containment And Retirement](#containment-and-retirement) | Backlog | `CONTAINMENT_EDGES` and falsifiers, with the collector |
| req-gitlab-neutral-links | [Neutral Links](#neutral-links) | Backlog | Project → `git_core` repository (the account half is `req-gitlab-person-link`) |
| req-gitlab-pipelines | [Execution Plane](#execution-plane) | Backlog | Pipelines, jobs, schedules |
| req-gitlab-domain-articles | [Domain Articles](#domain-articles) | Backlog | One article per type and edge |
| req-gitlab-nongoals | [Non-goals](#non-goals) | Implemented | What this plugin will not model |

---

### GitLab Instance Model
----
RID: `req-gitlab-model`

Status: `Implemented`

A GitLab instance: one self-managed GitLab (or gitlab.com), the outer node everything else belongs to. It
also carries the instance-wide settings that exist once per instance and that an assessor asks about first:
edition, version, FIPS mode, whether a password can still be used to sign in, whether 2FA is required,
whether anyone may register.

#### Implementation

`tap_plugin/gitlab/models/gitlab_instance.py`, `GitlabInstance`, `ENTITY_TYPE = "gitlab__gitlab_instance"`,
icon `gitlab-instance`, no default dimensions. Fields: `name` (required), `base_url`, `edition` (`ce`/`ee`),
`version`, `fips_mode`, `password_auth_enabled_for_web`, `password_auth_enabled_for_git`,
`require_two_factor`, `signup_enabled` (all booleans nullable), `tags`. v0's `configuration` field is removed
(see `req-gitlab-models-application-6`); migration `0002` drops the column and its history without copying
it. That is deliberate: v0 never observed anything, highbar's seed never wrote the field, and a grid that
did put a record there held exactly the secret material the removal exists to keep out.
`NATURAL_KEY = ("name",)`: a design-phase node carries only its name; revisited when the collector makes
`base_url` observable. Migration `0002_corpus_v1`.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-model-1 | Created Through The Service Layer | Implemented | A `create_node` write with only `name` succeeds and the row carries it. | `tests/test_gitlab_instance.py` |
| req-gitlab-model-2 | Name Required | Implemented | A `create_node` write without `name` is refused. | |
| req-gitlab-model-3 | Keyed By Name | Implemented | `NATURAL_KEY` is `("name",)` and every key field is a model field. | |
| req-gitlab-model-4 | Posture Unobserved Is Null | Implemented | The posture booleans are nullable; a node nobody observed reads null, not false. | |

---

### Infrastructure Models
----
RID: `req-gitlab-models-infrastructure`

Status: `Implemented`

The processes a GitLab deployment runs. `gitlab__gitlab_component` is one stateless process, its kind in a
`component` enum (webservice, workhorse, sidekiq, gitlab_shell, registry, kas, pages, mailroom, exporter,
toolbox, migrations). `gitlab__gitaly_node` is Gitaly, the one stateful process, its own type because it
alone owns a volume, is called by the others, and holds projects. `gitlab__runner_manager` is one running
GitLab Runner process: the executor, whether jobs run privileged, and its contact status live here, not on
the registration it authenticates as.

#### Implementation

`models/gitlab_component.py` (`GitlabComponent`), `models/gitaly_node.py` (`GitalyNode`),
`models/runner_manager.py` (`RunnerManager`). Each: `DEFAULT_DIMENSIONS = {"gitlab.plane": "infrastructure"}`
(`models/_schema.py`), `NATURAL_KEY = ("instance_name", "name")`, `CREATE_REQUIRED = ["instance_name",
"name"]`, `FIELD_VALIDATION_SCHEMA` derived from `FIELD_CRUD_SCHEMA` by `validation_schema()` (one
derivation). Shared observed fields: `image`, `version`, `fips_enabled`; components and Gitaly add `health`
(`healthy`/`degraded`/`unhealthy`, blank = not observed) and `health_observed_at`; components add `ports`
and `health_check`; Gitaly adds `storage_names` and `deployment_mode` (`standalone`/`praefect_cluster`); the
manager adds `system_id`, `executor`, `custom_driver`, `privileged`, `concurrent`, `status`, `contacted_at`,
`platform`, `architecture`.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-models-infrastructure-1 | Minimal Write | Implemented | A write with `instance_name` and `name` succeeds and carries `gitlab.plane: infrastructure`. | `tests/test_gitlab_models.py` |
| req-gitlab-models-infrastructure-2 | Required Fields | Implemented | Dropping either required field refuses the write. | |
| req-gitlab-models-infrastructure-3 | Instance In The Key | Implemented | The key rests on columns and begins with `instance_name`. | |
| req-gitlab-models-infrastructure-4 | Closed Vocabularies | Implemented | An unknown `component` value is refused. | |

---

### Application Models
----
RID: `req-gitlab-models-application`

Status: `Implemented`

The objects GitLab keeps that a FedRAMP 20x operator governs: `gitlab__gitlab_runner` (a runner
registration: scope, tags, untagged, protected refs only), `gitlab__gitlab_group`, `gitlab__gitlab_project`
(including the job-token allowlist and fork-pipeline settings), `gitlab__gitlab_user` (people, service
accounts and token bot users, by `user_type`), `gitlab__protected_branch`, `gitlab__gitlab_environment`
(protection as fields), `gitlab__ci_variable` (never the value), `gitlab__deploy_key`,
`gitlab__deploy_token`, `gitlab__access_token` (never the secret), `gitlab__sso_provider`,
`gitlab__audit_event_destination`.

#### Implementation

One module per type under `models/`, each with `DEFAULT_DIMENSIONS = {"gitlab.plane": "application"}` and a
key beginning with `instance_name`: runner, deploy key, SSO provider and audit destination on `name`; group
and project on `full_path`; user on `username`; protected branch and environment on
`(project_path, name)`; CI/CD variable on `(scope, scope_path, key, environment_scope)`, where an
instance-level variable's `scope_path` and `environment_scope` are empty because its `scope` says they do
not apply; deploy token on `(scope_path, name)`; access token on `(owner_path, name)`. Credentials carry
`expires` (false is the finding: never expires) beside `expires_at`, so "never expires" and "not observed"
are different values. GitLab's numeric ids (`runner_id`, `group_id`, `project_id`, `user_id`,
`deploy_key_id`, `deploy_token_id`, `token_id`) are nullable columns, not keys. **No type has a free-form `configuration` field**, the
instance included: GitLab's source records carry secret material — a variable's value, a token, an OIDC
client secret, an audit destination's verification token or access key, a runner manager's `config.toml`
runner token, a component's database password, the instance's application-setting keys — so only promoted
columns are stored, and a collector cannot persist a secret into the live or historical tables by passing a
record through. The one free-text field that could still carry a credential, an audit destination's
`destination_url`, is constrained to scheme, host and path (no user info, query or fragment).

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-models-application-1 | Minimal Write | Implemented | A write with the required fields succeeds, carries `gitlab.plane: application`, and is named from its key. | `tests/test_gitlab_models.py` |
| req-gitlab-models-application-2 | Required Fields | Implemented | Dropping any required field refuses the write. | |
| req-gitlab-models-application-3 | Instance In The Key | Implemented | Every key rests on columns and begins with `instance_name`. | |
| req-gitlab-models-application-4 | Unobserved Booleans Are Null | Implemented | A boolean nobody wrote reads null, never false. | |
| req-gitlab-models-application-5 | Every Manifest Type Covered | Implemented | A type added to the manifest without a test case fails by name. | |
| req-gitlab-models-application-6 | No Raw Record | Implemented | No type (instance included) declares an object-typed field other than the instance's `tags` labels; a write carrying a value or token in an undeclared field is refused. | Applies to the infrastructure types too. |
| req-gitlab-models-application-7 | No Credential In A URL | Implemented | An audit destination URL with user info, a query or a fragment is refused. | `test_destination_url_carries_no_credential` |

---

### Infrastructure Edges
----
RID: `req-gitlab-edges-infrastructure`

Status: `Implemented`

What a process belongs to, where it runs, and what it reaches. Every edge whose far end is the platform
underneath leaves that end open (the description names what may appear there), so this plugin names no
AWS type: `RUNS_COMPONENT` (instance → component, Gitaly), `RUNS_ON_SERVICE` (process → *open*:
`container_name`), `CALLS_GITALY` (component → Gitaly: `storage_names`, `tls`), `QUERIES_DATABASE`
(component, Gitaly → *open*: `database` required, `role`, `tls_mode`), `CALLS_REDIS` (component → *open*:
`redis_role` required, `tls`), `STORES_OBJECTS` (component, manager → *open*: `object_type` required, `auth`),
`STORES_REPOSITORIES_ON_VOLUME` (Gitaly → *open*: `storage_name`, `mount_path`, `filesystem`),
`READS_SECRET` (process → *open*: `purpose`, `delivery`), `AUTHENTICATES_AS_RUNNER` (manager → runner),
`LAUNCHES_JOB_TASKS` (manager → *open*: `platform` required). Ingress is aws_core's `ROUTES_TRAFFIC` from a
load balancer to a component; this plugin does not define a second edge for it.

#### Implementation

`edges/<SLUG>.edge.json`, each `<SLUG>__gitlab`, registered under `[edges]`; `property_schema` with
`additionalProperties: false` wherever properties exist; `default_dimensions: {"gitlab.plane":
"infrastructure"}`. No model declares `OUTBOUND_EDGES` or `CONTAINMENT_EDGES` (see
`req-gitlab-containment`), so, as observed in `tests/test_gitlab_edges.py`, the grid does not refuse an edge
whose source is outside the declared list: the lists document the vocabulary and drive `validate_plugin`'s
create-edge check.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-edges-infrastructure-1 | Own Types Or Open | Implemented | Every endpoint names a `gitlab__` type or is omitted; an omitted target says "open" in its description. | `tests/test_gitlab_edges.py` |
| req-gitlab-edges-infrastructure-2 | Closed Properties | Implemented | Every property schema forbids undeclared keys. | |
| req-gitlab-edges-infrastructure-3 | Plane Stamped | Implemented | Every edge stamps `gitlab.plane`. | |
| req-gitlab-edges-infrastructure-4 | Open End Accepts Foreign Types | Implemented | A component `RUNS_ON_SERVICE` an aws_core ECS service. | |

---

### Application Edges
----
RID: `req-gitlab-edges-application`

Status: `Implemented`

Hierarchy (`HOSTS_GROUP`, `NESTS_SUBGROUP`, `HOLDS_PROJECT`, `HOLDS_ACCOUNT`), membership with the role on
the edge (`MEMBER_OF_GROUP`, `MEMBER_OF_PROJECT`, `INVITES_GROUP`: `role` required, `access_level`,
`expires_at`; direct membership only, inherited is derived), runner scope (`REGISTERS_RUNNER`: `assignment`),
protections (`DECLARES_PROTECTED_BRANCH`, `PERMITTED_ON_BRANCH`: `action` required; `DECLARES_ENVIRONMENT`,
`PERMITTED_ON_ENVIRONMENT`: `action` required, `required_approvals`), variables (`DEFINES_VARIABLE`),
credentials (`ENABLES_DEPLOY_KEY`: `can_push` required, because write access is per project;
`ISSUES_DEPLOY_TOKEN`; `ISSUES_ACCESS_TOKEN`; `AUTHENTICATES_AS_USER`), sign-in
(`AUTHENTICATES_VIA_PROVIDER`, `SIGNS_IN_VIA_PROVIDER`: `extern_uid`; `TRUSTS_SAML_IDP` → *open*:
`idp_entity_id`, `idp_cert_fingerprint_sha256`), audit (`STREAMS_AUDIT_EVENTS`, `DELIVERS_EVENTS` → *open*),
storage (`RESIDES_ON_GITALY`: `storage_name`) and the job-token allowlist (`ALLOWLISTS_JOB_TOKEN`). An OIDC
sign-in provider trusts its issuer through identity_core's `TRUSTS_ISSUER` to an `identity_core__oidc_issuer`
— the substrate already holds the issuer URL, so the provider does not copy it.

#### Implementation

As for the infrastructure edges, with `default_dimensions: {"gitlab.plane": "application"}`. `identity_core`
is in `depends_on` as a vocabulary dependency for `TRUSTS_ISSUER`.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-edges-application-1 | Own Types Or Open | Implemented | As for infrastructure edges. | `tests/test_gitlab_edges.py` |
| req-gitlab-edges-application-2 | Required Property Enforced | Implemented | `ENABLES_DEPLOY_KEY` without `can_push`, or with an undeclared property, is refused. | |
| req-gitlab-edges-application-3 | Slugs Name An Action And Object | Implemented | `validate_plugin`'s edge-naming check passes with no baseline. | |

---

### Person Link
----
RID: `req-gitlab-person-link`

Status: `Implemented`

A GitLab user account that a person holds resolves to that person: `identity_core__human` (a neutral
substrate type keyed on an operator-assigned handle), through identity_core's `HELD_BY_HUMAN__identity_core`,
whose source is wildcard so no substrate depends upward on GitLab. The same person's Okta, Duo and Teleport
accounts point at the same node, which is what an access review joins on. `gitlab__gitlab_user` holds people,
service accounts and token bot users in one type, so the edge is drawn only for an account a person holds;
a service account or bot user has none, and neither does an account nobody has matched yet (the unmatched
state an access review must show). The edge is drawn by whoever knows the match (an operator's seed, an HR
feed, a collector matching an immutable id) and records how in `matched_on`; it is never inferred from a
shared email or display name. An account held by two people (a shared login) keeps both edges.

#### Implementation

`GitlabUser.OUTBOUND_EDGES` declares `{"nodes": [{"type": "identity_core__human"}], "edges": [{"type":
"HELD_BY_HUMAN__identity_core"}]}`. Under the permission union (`tap_grid/constraints.py::validate_edge`) this
adds one permission and constrains nothing else: every gitlab edge from a user is still permitted by its own
edge file. `identity_core` was already in `depends_on`; its note now names this edge too, and the `ci`
record's identity_core pin moved to the first commit carrying the human.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-person-link-1 | Declared | Implemented | `GitlabUser` declares `HELD_BY_HUMAN__identity_core` to `identity_core__human` in `OUTBOUND_EDGES`, and `identity_core` is in `depends_on`. | `test_person_link_is_declared` |
| req-gitlab-person-link-2 | Written Through The Service Layer | Implemented | A user writes `HELD_BY_HUMAN__identity_core` to a human with `matched_on`; an unknown property is refused. | `test_account_is_held_by_a_human` |
| req-gitlab-person-link-3 | Shared Account Recorded | Implemented | One user may be held by two humans; both edges stand. | `test_shared_account_is_recorded` |
| req-gitlab-person-link-4 | Nothing Else Constrained | Implemented | Declaring `OUTBOUND_EDGES` leaves the user's own gitlab edges (`MEMBER_OF_PROJECT`, `SIGNS_IN_VIA_PROVIDER`) writable. | `test_own_edges_still_permitted` |

---

### Icons Requirement
----
RID: `req-gitlab-icons`

Status: `Implemented`

Every type has its own icon, drawn for this plugin. GitLab's trademark guidelines (read 2026-09-22, "last
modified 2026-08-27") do not permit use of the tanuki logo outside an unmodified GitLab distribution, and
the MIT licence of `gitlab-svgs` explicitly does not cover the trademarks; v0's `gitlab-instance` icon (the
tanuki) is replaced.

#### Implementation

`static/gitlab/icons/<key>.svg`, 64×64 with `viewBox="0 0 64 64"`, stroke glyphs: infrastructure types in
`#E24329`, application types in `#6B4FBB`. Keys: `gitlab-instance` (a server stack), `gitlab-component`,
`gitlab-gitaly`, `gitlab-runner-manager`, `gitlab-runner`, `gitlab-group`, `gitlab-project`,
`gitlab-user`, `gitlab-protected-branch`, `gitlab-environment`, `gitlab-ci-variable`, `gitlab-deploy-key`,
`gitlab-deploy-token`, `gitlab-access-token`, `gitlab-sso-provider`, `gitlab-audit-destination`.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-icons-1 | Square And Sized | Implemented | Every type's icon exists with `width="64" height="64"` and a square viewBox. | `tests/test_gitlab_icons.py` |
| req-gitlab-icons-2 | No Vendor Logo | Implemented | No icon is GitLab's logo. | |

---

### Deployment Layout
----
RID: `req-gitlab-layout`

Status: `Implemented`

A tap layout module that draws each GitLab instance in a scene as one box: load balancers on the left
(ingress), each process nested inside the compute service it runs on (compute), the runner managers' services,
job platforms and runner registrations under them (runners), the databases, Redis, volumes, object stores
and secrets to the right (data stores, wrapping every six), sign-in providers and audit destinations last,
and the identity providers and event sinks they trust or deliver to outside the box. It names no entity id
and no instance, so any page whose scene holds GitLab nodes can use it; several instances draw side by side.

#### Implementation

`static/gitlab/js/projections/gitlab-deployment.js`, `export async function execute(context)`
(`req-viz-layout-module-contract`). Service ⊃ process comes from `RUNS_ON_SERVICE` directly (the nesting
runtime's inbound pattern); instance ⊃ everything its deployment reaches from synthetic `_GITLAB_DEPLOYS`
edges added on every entry and removed on re-entry. Graph node data carries label, type, dimensions and
tags — not model fields — so ownership is derived from edges: `RUNS_COMPONENT`, `REGISTERS_RUNNER`,
`AUTHENTICATES_VIA_PROVIDER`, `STREAMS_AUDIT_EVENTS` from the instance; a manager through the runner it
authenticates as; a foreign node through the GitLab process at the other end of its edge. A band is decided
by the edge that reached a node, never its type. A node reached from two instances is drawn in the first and
warned; a node reached from none is drawn under the picture and warned — never dropped. Sizing and chrome
come from tap_viz's `projectNested`, `applyStandardChrome` and `placeParentLabels`; band captions are
synthetic label nodes carrying their own colours.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-layout-1 | No Ids | Implemented | The module names no entity id and no instance. | Read. |
| req-gitlab-layout-2 | Places The Reference Deployment | Implemented | Against the example deployment's scene it places every node, nests each process in its service and every owned node in the instance, puts the OIDC issuer outside, and warns nothing. | Observed 2026-09-22 by running the module headless (cytoscape 3, JavaScriptCore) over the fixture scene; not yet observed in a browser. |
| req-gitlab-layout-3 | Nothing Dropped | Implemented | An unowned node is drawn under the picture with a warning. | Read. |

---

### Posture Strip Panel
----
RID: `req-gitlab-panel-posture`

Status: `Implemented`

A panel type that names the instance the page shows (with links to each when there are several) and then one
tile per posture question, each tile declared in the panel instance's config: a population query, a finding
query, an optional unobserved query, an optional secondary query, and a tone. The population is only the
objects whose deciding fact was **observed** (a variable whose `protected` is not null, a Gitaly node whose
volume's `filesystem` is recorded), so an object nobody looked at can never make a tile read clear; the
unobserved query counts the rest and the tile says how many. A tile whose population is empty reads *not
observed*; a failed query reads *could not read* (the detail goes to the server log, not the page); only a
populated, answered tile shows a count.

#### Implementation

`panels/posture/__init__.py`, `PosturePanelType` (slug `gitlab-posture`, view `gitlab/panels/posture.html`,
css `gitlab/css/posture.css`), registered in `GitlabConfig.ready()`. Reads through
`execute_gryphon_raw(..., layer="full")`; counts are envelope node counts. Inputs supplied to a query only
if it names them: `instance` (the page's `?instance=`) and `cutoff` (now + 30 days, ISO 8601). Tile config:
`{key, label, help, population, finding, unobserved?, secondary?: {label, query}, tone: bad_if_any |
good_if_any}`. When the selected name is both the start and the end of another instance's name, the strip
says the page cannot tell them apart (see `req-gitlab-page`).

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-panel-posture-1 | Three States | Implemented | A type absent for the instance reads not observed; a populated tile counts; an error reads could not read. | `tests/test_gitlab_page.py` |
| req-gitlab-panel-posture-4 | Unobserved Never Clear | Implemented | An object whose deciding fact is null is outside the population and counted as unobserved; a tile holding only such objects reads not observed. | A CI variable with `protected` null; the fixture's Gitaly with no volume edge. |
| req-gitlab-panel-posture-5 | Overlapping Names Said | Implemented | Selecting a name that another instance's name begins and ends with puts a note on the strip. | `tests/test_gitlab_posture.py` |
| req-gitlab-panel-posture-2 | Null Is Not Revoked | Implemented | A token whose `revoked` was never observed still counts as live. | |
| req-gitlab-panel-posture-3 | Every Tile Answers | Implemented | Every tile the page configures runs without error against the example deployment. | |

---

### GitLab Page
----
RID: `req-gitlab-page`

Status: `Implemented`

`/gitlab` is one instance's front page for an operator in a FedRAMP 20x environment: the deployment graph at
the top (66vh), the posture strip, then tables — Components, Gitaly, Runners, Runner managers, Projects,
Protected branches, Environments, CI/CD variables, Access tokens, Deploy keys, Deploy tokens, Accounts,
Sign-in providers, Audit event streaming. `?instance=<name>` selects the instance by its name (its natural
key); blank selects every instance, which is the single instance when there is one.

#### Implementation

`grift/gitlab-page.grift.json` (`[grift] gitlab_page`), batch `gitlab page v0.1.1`: the page, the graph
panel (`tap_viz/panels/graph_panel.html`) with its projection (`node_style: icon-badge`, `lock_nodes`,
`min_zoom: fit`), elevation and layout, 23 scene searches each naming its edge type (one per edge type and
labelled GitLab source type, because Gryphon filters a field only on a labelled variable), the posture panel
with 13 tiles, and 14 standard table panels (`tap_web/panels/table_panel.html`) each over an envelope-mode
search. Every search declares `instance` with `default: ""` (`req-grid-search-obj-5-2`) and filters with
`instance_name STARTS_WITH $instance AND instance_name ENDS_WITH $instance` — Gryphon has no
param-absent predicate yet (tap#360), and a string operator on `entity_id` is refused, so the page keys on
the instance's name rather than its entity id. The filter is **not** exact when one instance's name both begins and
ends with another's (`aba` also selects `ababa`); the posture strip says so when it happens, and the tables
cannot. Name instances so that none begins and ends with another (`staging`, `production`) until tap#360
lands, then switch every search to equality. The graph's scene includes aws_core's `ROUTES_TRAFFIC` into a component, which is why
`aws_core` is a declared vocabulary dependency.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-gitlab-page-1 | Imports | Implemented | The bundle imports with its hotlinks satisfied. | `tests/test_gitlab_page.py` |
| req-gitlab-page-2 | Every Search Runs | Implemented | Every search runs blank, named and unknown; unknown returns nothing. | |
| req-gitlab-page-3 | Prefix Selects Nothing | Implemented | A prefix of the instance's name selects nothing. | Not exact equality: see the overlap note above. |
| req-gitlab-page-7 | Overlapping Names Kept Apart | Backlog | Selecting `aba` never returns `ababa`'s rows. | Blocked on tap#360; `test_overlapping_names_do_not_mix` is a strict xfail that flips when it lands. |
| req-gitlab-page-4 | Scene Covers The Deployment | Implemented | The scene searches together return every node of the example deployment that the vocabulary reaches. | The GitLab ECS cluster is not reached: aws_core has no cluster→service edge. |
| req-gitlab-page-5 | Tables Get Nodes | Implemented | A table search returns typed nodes (envelope mode). | |
| req-gitlab-page-6 | Renders | Proposed | The page renders in a browser with every slot filled and no console error. | Not yet observed: the page has not been booted into a stack. |

---

### CI Record and Tests
----
RID: `req-gitlab-record`

Status: `Implemented`

The in-package `ci` boot record (`req-boot-bootstrap-ci-record`) and the tests that run in it.

#### Implementation

`boot/ci.boot.json` installs `identity_core` and `aws_core` (the depends_on closure; neither declares
dependencies), each pinned to a full commit SHA (identity_core at the first commit carrying `identity_core__human`), and this plugin, and seeds this plugin's page bundle. `tests/test_gitlab_manifest.py` runs
`validate_plugin` at structure and strict levels; `test_gitlab_instance.py`, `test_gitlab_models.py`,
`test_gitlab_edges.py`, `test_gitlab_person.py`, `test_gitlab_icons.py`, `test_gitlab_page.py` and `test_gitlab_posture.py` cover the requirements above;
`tests/fixtures/example-deployment.grift.json` is the reference deployment (not declared in the manifest,
never seeded).

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

Observe a real GitLab onto the grid: the REST API for the application plane (an administrator or auditor
token; several listings — `GET /deploy_keys`, instance variables, service accounts — are admin-only), the
health endpoints for the infrastructure plane, and the runner managers' `config.toml` (the only source of
`privileged`). Keys move to GitLab's numeric ids once observed.

---

### Containment And Retirement
----
RID: `req-gitlab-containment`

Status: `Backlog`

The delete tree is designed but not declared: an instance contains its components and Gitaly nodes; a
project contains its protected branches, environments and variables; a group or project its deploy tokens
and access tokens. Shared things are references: a deploy key (enabled on many projects), a user, a runner
(enabled on many projects). Declaring `CONTAINMENT_EDGES` makes each target reconcilable and requires a
falsifier (`req-grid-reconcile-falsifier-2`); both land with the collector.

---

### Neutral Links
----
RID: `req-gitlab-neutral-links`

Status: `Backlog`

`gitlab__gitlab_project` → `git_core__git_repository` (the settled `HOSTS_REPOSITORY` pattern), once a
collector reads both sides. Accounts to the identity substrate moved to `req-gitlab-person-link`.

---

### Execution Plane
----
RID: `req-gitlab-pipelines`

Status: `Backlog`

Pipelines, jobs, pipeline schedules and job artifacts as runs, with the protected-variable and runner reach
of each: the git-serious shape for GitLab.

---

### Domain Articles
----
RID: `req-gitlab-domain-articles`

Status: `Backlog`

One article per node and edge type under `domain/` (`spec-domain-articles.md`). The corpus
([corpus-gitlab.md](corpus-gitlab.md)) holds each type's justification until then.

---

### Non-goals
----
RID: `req-gitlab-nongoals`

Status: `Implemented`

Not modelled, by decision: issues, epics and merge requests as work-tracking objects; group SAML settings
(gitlab.com only); leaked-secret findings (a scanner's findings, not a GitLab object); the values of
variables and the secrets of tokens.

## Model catalog

Superseded by the manifest as of v0.2.0; only the decisions the code cannot state remain. The full
justification per type is in [corpus-gitlab.md](corpus-gitlab.md).

| Model | Entity type | Category | Rationale |
| --- | --- | --- | --- |
| `GitlabComponent` | `gitlab__gitlab_component` | Infrastructure | One type with a `component` enum: nothing points at one component kind differently. Workhorse is its own value because it is its own container and the ALB's target. |
| `GitalyNode` | `gitlab__gitaly_node` | Infrastructure | The one stateful process; the support caveat and the volume live here. |
| `RunnerManager` | `gitlab__runner_manager` | Infrastructure | Split from the registration: one registration, many managers; the executor is the manager's. |
| `GitlabUser` | `gitlab__gitlab_user` | Application | People, service accounts and bot users in one type, as GitLab stores them. |
| `CiVariable` | `gitlab__ci_variable` | Application | One type for all three scopes; the value is never a field. |
| `AccessToken` | `gitlab__access_token` | Application | One type for four token kinds; who issued it is an edge. |

## Edge types

Superseded by the manifest as of v0.2.0; decisions only.

| Edge | From → To | Properties | Rationale |
| --- | --- | --- | --- |
| `RUNS_ON_SERVICE__gitlab` and every edge to the platform | GitLab process → open | per edge | The far end is the deployment's choice; naming aws_core types would make every new platform an edit here. |
| `MEMBER_OF_GROUP__gitlab` | user → group | `role`, `access_level` | Roles are properties of the relationship, not nodes (Cartography's choice over GitLabHound's). |
| `ENABLES_DEPLOY_KEY__gitlab` | project → deploy key | `can_push` | Write access is per project, so it cannot live on the key. |
| `AUTHENTICATES_AS_USER__gitlab` | access token → user | — | One edge serves personal tokens (owner) and group/project tokens (bot user) alike. |
| (none) | load balancer → component | — | Ingress is aws_core's `ROUTES_TRAFFIC`; a second edge would be the same fact twice. |

## Icons

GitLab's logo is a trademark its guidelines do not license for this use, so every icon here is this
plugin's own glyph (`req-gitlab-icons`).
