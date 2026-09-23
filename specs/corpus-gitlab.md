# GitLab Vocabulary Corpus

**The justification for every type and edge `gitlab` models: what the field already calls each concept, which
sources and failures demand it, what was rejected, and where to look when GitLab moves. Dated 2026-09-22;
this is a maintained artefact, not a final one.** The spec ([spec-gitlab-v0.md](spec-gitlab-v0.md)) states
the requirements; this file is the aggregate "why" behind them (build-domain-vocabulary, Step 7).

## Domain and boundary

- **In scope.** A small, professional, self-managed GitLab that ships an organisation's core
  infrastructure: its deployed processes, what they run on and store to, its runners, and the objects
  inside it that a FedRAMP 20x operator governs (who can reach what, which credentials exist and how long
  they live, where sign-in and audit go).
- **Out of scope.** gitlab.com as a SaaS estate; GitLab's work-tracking plane (issues, epics, merge
  requests as review objects); the execution plane (pipelines, jobs, job logs, artifacts as runs) — the
  git-serious product models execution for GitHub and would model it for GitLab; the neutral Git objects
  (commits, refs), which belong to `git_core`.
- **First use case.** highbar's staging `cicd` account: one GitLab on ECS with Chainguard FIPS images and
  Fargate-launched CI jobs, drawn as a design before anything is built, then observed.

## Node inventory

Neutral? — could a structurally different forge populate the type unchanged. Status as of this revision:
all built.

| Type | Neutral? | Tier | Justification (sources) |
| --- | --- | --- | --- |
| `gitlab__gitlab_instance` | vendor | 1 | GitLabHound `GL_Instance`; GitLab reference architectures; the outer node every other type belongs to. |
| `gitlab__gitlab_component` | vendor | 1 | GitLab chart component list (webservice, Workhorse, Sidekiq, Shell, registry, KAS, Pages, Mailroom, exporter, toolbox); Chainguard's 15-image GitLab set; reference architectures' "stateless in containers" split. One type with a `component` enum: nothing points at one component kind differently from another. |
| `gitlab__gitaly_node` | vendor | 1 | Reference architectures (Gitaly is the one component that must not be treated as stateless); GitLab Gitaly docs (local storage only, no NFS/EFS). Its own type because it alone owns a volume, receives CALLS_GITALY and holds projects (RESIDES_ON_GITALY). |
| `gitlab__runner_manager` | vendor | 1 | GitLab Runner API (`/runners/:id/managers`, `system_id`); the executor docs; OMGCICD (privileged docker runner escape). Split from the registration because one registration has many managers and the executor lives on the manager. |
| `gitlab__gitlab_runner` | vendor | 2 | Cartography `GitLabRunner`; GitLab Runner API; Glato/Trajan (self-hosted runner enumeration). Scope, tags, run-untagged and access level decide whose jobs it takes. |
| `gitlab__gitlab_group` | vendor | 2 | Cartography `GitLabGroup`/`GitLabOrganization`; GitLabHound `GL_Group`; GitLab API. |
| `gitlab__gitlab_project` | vendor | 2 | Cartography `GitLabProject`; GitLabHound `GL_Project`; GitLab API. Links to the neutral `git_core__git_repository` are Backlog (`req-gitlab-neutral-links`). |
| `gitlab__gitlab_user` | vendor | 2 | Cartography `GitLabUser`; GitLabHound `GL_User`; GitLab Users and Service Accounts APIs. One type for people, service accounts and token bot users, separated by `user_type`. |
| `gitlab__protected_branch` | vendor | 2 | GitLab Protected Branches API; GitLabHound `GL_CanPush`/`GL_CanMerge`; CVE-2023-4812 (Code Owner approval bypass). Not in Cartography. |
| `gitlab__gitlab_environment` | vendor | 2 | Cartography `GitLabEnvironment`; GitLab Environments and Protected Environments APIs. Protection is fields on the same object, not a second type. |
| `gitlab__ci_variable` | vendor | 2 | Cartography `GitLabCIVariable`; GitLabHound `GL_Variable` family; the unprotected-variable-to-fork-pipeline failure. The value is never modelled. |
| `gitlab__deploy_key` | vendor | 2 | GitLab Deploy Keys API; OMGCICD (a deploy SSH key harvested from a job reached production). Not in any prior graph model. |
| `gitlab__deploy_token` | vendor | 2 | GitLab Deploy Tokens API. Not in any prior graph model. |
| `gitlab__access_token` | vendor | 2 | GitLabHound `GL_AccessToken` family; GitLab PAT and group/project token APIs. One type with `token_type`: the kinds differ in who issued them, which is an edge. |
| `gitlab__sso_provider` | vendor | 2 | GitLab OmniAuth SAML/OIDC docs (instance-wide on self-managed); CVE-2023-7028 (password reset takeover, mitigated by SSO-only sign-in). Not in any prior graph model. |
| `gitlab__audit_event_destination` | vendor | 2 | GitLab audit event streaming docs (HTTP, S3, Google Cloud Logging; Ultimate). FedRAMP 20x logging expectations. Not in any prior graph model. |

**Ahead of the prior art.** No graph model we found carries deploy keys, deploy tokens, protected
environments, audit streaming destinations, the job-token allowlist, or sign-in provider configuration.
Those are the objects a FedRAMP assessor asks about first, which is why they are here.

## Edge inventory

| Edge | From → To | Properties (the question each settles) | Justification |
| --- | --- | --- | --- |
| `RUNS_COMPONENT__gitlab` | instance → component, gitaly | — (membership; the node carries the facts) | Reference architectures' component lists. |
| `RUNS_ON_SERVICE__gitlab` | component, gitaly, manager → *open* | `container_name` (which container in a shared task) | ECS ruling; webservice and Workhorse share one task. |
| `CALLS_GITALY__gitlab` | component → gitaly | `storage_names`, `tls` (is component-to-component traffic encrypted — FIPS) | GitLab FIPS doc: communication between components must be compliant. |
| `QUERIES_DATABASE__gitlab` | component, gitaly → *open* | `database` (main/ci/registry/praefect), `role`, `tls_mode` | GitLab database decomposition; RDS support; Aurora unsupported. |
| `CALLS_REDIS__gitlab` | component → *open* | `redis_role`, `tls` | GitLab Redis roles; ElastiCache for Valkey guidance. |
| `STORES_OBJECTS__gitlab` | component, manager → *open* | `object_type` (which of GitLab's object kinds), `auth` (IAM role or static keys) | GitLab consolidated object storage list; one bucket per type recommended. |
| `STORES_REPOSITORIES_ON_VOLUME__gitlab` | gitaly → *open* | `storage_name`, `mount_path`, `filesystem` (is it an unsupported NFS/EFS mount) | Gitaly local-storage-only statement. |
| `READS_SECRET__gitlab` | component, gitaly, manager → *open* | `purpose`, `delivery` | Chainguard/ECS deployment wiring (gitlab-secrets.json, DB and Redis passwords, runner token). |
| `AUTHENTICATES_AS_RUNNER__gitlab` | manager → runner | — | Runner managers API. |
| `LAUNCHES_JOB_TASKS__gitlab` | manager → *open* | `platform` (Fargate, EC2 ASG, Kubernetes…) | Fargate driver docs; fleeting docs. |
| `HOSTS_GROUP__gitlab` | instance → group | — | GitLab namespaces. |
| `NESTS_SUBGROUP__gitlab` | group → group | — | Cartography `MEMBER_OF` (Group→Group); CVE-2023-2825 needed the nesting depth. |
| `HOLDS_PROJECT__gitlab` | group, user → project | — | Namespaces hold projects. |
| `HOLDS_ACCOUNT__gitlab` | instance → user | — | Instance-level user list. |
| `MEMBER_OF_GROUP__gitlab` | user → group | `role`, `access_level`, `expires_at` | Cartography / GitLabHound membership; Members API. Direct membership only; inherited is derived. |
| `MEMBER_OF_PROJECT__gitlab` | user → project | same | same |
| `INVITES_GROUP__gitlab` | group, project → group | same | GitLabHound `GL_InvitedTo`; group sharing. |
| `REGISTERS_RUNNER__gitlab` | instance, group, project → runner | `assignment` (owner or enabled) | Runners API; runner scopes. |
| `DECLARES_PROTECTED_BRANCH__gitlab` | project, group → protected branch | — | Protected Branches API. |
| `PERMITTED_ON_BRANCH__gitlab` | user, group, deploy key → protected branch | `action` (push/merge/unprotect) | Per-user/group/deploy-key grants in the access-level lists. |
| `DECLARES_ENVIRONMENT__gitlab` | project → environment | — | Environments API. |
| `PERMITTED_ON_ENVIRONMENT__gitlab` | user, group → environment | `action` (deploy/approve), `required_approvals` | Protected Environments API. |
| `DEFINES_VARIABLE__gitlab` | instance, group, project → variable | — | Cartography `HAS_CI_VARIABLE`; GitLabHound `GL_Defines`. |
| `ENABLES_DEPLOY_KEY__gitlab` | project → deploy key | `can_push` (write access is per project) | Deploy Keys API (`projects_with_write_access`). |
| `ISSUES_DEPLOY_TOKEN__gitlab` | group, project → deploy token | — | Deploy Tokens API. |
| `ISSUES_ACCESS_TOKEN__gitlab` | group, project → access token | — | Group/project token APIs. |
| `AUTHENTICATES_AS_USER__gitlab` | access token → user | — | GitLabHound `GL_HasPrivilegeOf`; the bot user behind group/project tokens. |
| `AUTHENTICATES_VIA_PROVIDER__gitlab` | instance, group → SSO provider | — | OmniAuth providers. |
| `SIGNS_IN_VIA_PROVIDER__gitlab` | user → SSO provider | `extern_uid` | Users API `identities[]`. |
| `TRUSTS_SAML_IDP__gitlab` | SSO provider → *open* | `idp_entity_id`, `idp_cert_fingerprint_sha256` (what trust is pinned to) | GitLab SAML config. OIDC uses identity_core's `TRUSTS_ISSUER`. |
| `STREAMS_AUDIT_EVENTS__gitlab` | instance, group → destination | — | Audit event streaming. |
| `DELIVERS_EVENTS__gitlab` | destination → *open* | — | Streaming destinations (S3, HTTP). |
| `RESIDES_ON_GITALY__gitlab` | project → gitaly | `storage_name` | Repository storage assignment; the blast radius of a Gitaly volume. |
| `ALLOWLISTS_JOB_TOKEN__gitlab` | project → project, group | — | Job token scope API; CI_JOB_TOKEN lateral movement. |

Open ends (*open*) are deliberate (add-edge, "Cross-plugin endpoints"): what hosts a process or stores its
objects is the deployment's choice, so the AWS types sit at the far end of the edge without this plugin
naming them. Ingress uses aws_core's own `ROUTES_TRAFFIC` (load balancer → component) rather than a second
edge for the same fact.

## Rejected candidates

| Candidate | Where it went | Why |
| --- | --- | --- |
| Separate node per component kind (webservice, Sidekiq, …) | `component` enum on `gitlab__gitlab_component` | Nothing points at one kind differently; one type keeps the query surface small. Gitaly is the exception and has its own type. |
| Workhorse folded into webservice | its own `component` value | Chainguard ships it as a separate image and ECS runs it as its own container; the ALB routes to it, not to Puma. |
| Role nodes (GitLabHound `GL_*Role`) | `role` / `access_level` properties on membership edges | A role is the fact about the relationship; a node per role per group multiplies nodes without a question it alone answers. Revisit if custom roles (Ultimate) arrive. |
| Protected environment as its own type | fields on `gitlab__gitlab_environment` | Same object in GitLab's API; protection is a state of it. |
| Instance/group/project variable types (GitLabHound) | one `gitlab__ci_variable` with `scope` | Scope is a property; the edges say who defines it. |
| Personal/group/project token types | one `gitlab__access_token` with `token_type` | Same fields; issuer is an edge. |
| Bot user as a separate type | `gitlab__gitlab_user` with `user_type` | GitLab stores it as a user; tokens reach it with `AUTHENTICATES_AS_USER`. |
| Branch (Cartography `GitLabBranch`) | `git_core` (neutral refs), Backlog link | A branch is a Git ref, not a GitLab object; the GitLab-specific fact is the protection rule. |
| Pipeline, job, job log, artifact, pipeline schedule | Backlog (`req-gitlab-pipelines`) | Execution plane; a separate tier with its own collector and volume. |
| Merge request, issue, epic | not modelled (`req-gitlab-nongoals`) | Work tracking, not the platform's security surface. |
| Group SAML settings (enforce SSO for web/Git) | not modelled on self-managed | gitlab.com only; self-managed sign-in is instance-wide OmniAuth. |
| Leaked secret (GitLabHound `GL_LeakedSecret`) | not modelled | A finding, not an object: belongs to a scanner plugin's findings against the variable or log it came from. |
| Praefect as a component | `deployment_mode` on Gitaly, Backlog | Not needed below ~2,000 users; the reference deployment has one Gitaly. |
| `storage_backend` field on Gitaly | `filesystem` on `STORES_REPOSITORIES_ON_VOLUME` | The fact is about the mount, and the volume's type is the far node. |
| Issuer URL field on the SSO provider | `TRUSTS_ISSUER__identity_core` → `identity_core__oidc_issuer` | identity_core already holds the issuer URL; a copy here would be the same fact twice. |
| An instance dimension (`gitlab.instance: <name>`) | `instance_name` key column | Dimensions are ignored by natural-key lookup (`req-grid-entity-natural-key-10`); identity needs a column. |

## Source register

| Source | Version / date read | URL | Artefact to watch | Verdict |
| --- | --- | --- | --- | --- |
| GitLab reference architectures (1k, 2k, index "Unsupported designs") | docs.gitlab.com, current at 2026-09-22 (GitLab 19.x) | https://docs.gitlab.com/administration/reference_architectures/ | GitLab docs repo (`doc/administration/reference_architectures`) | adopt |
| GitLab Helm chart component list | 2026-09-22 | https://docs.gitlab.com/charts/charts/gitlab/ | `gitlab-org/charts/gitlab` releases | adopt (names) |
| Gitaly storage support statement | 2026-09-22 | https://docs.gitlab.com/administration/gitaly/ | docs repo | adopt |
| Object storage (consolidated form) | 2026-09-22 (mentions 19.4) | https://docs.gitlab.com/administration/object_storage/ | docs repo | adopt (`object_type` enum) |
| Load balancer and health checks | 2026-09-22 | https://docs.gitlab.com/administration/load_balancer/ , https://docs.gitlab.com/administration/monitoring/health_check/ | docs repo | adopt |
| Install requirements (PostgreSQL, Redis) and cloud services | 2026-09-22 | https://docs.gitlab.com/install/requirements/ , https://docs.gitlab.com/install/cloud-services/ | docs repo | adopt |
| Runner executors, Fargate driver, fleeting | 2026-09-22 | https://docs.gitlab.com/runner/executors/ , https://docs.gitlab.com/runner/configuration/runner_autoscale_aws_fargate/ | `gitlab-org/gitlab-runner` releases | adopt |
| GitLab REST API: runners, members, protected branches/environments, variables, deploy keys/tokens, access tokens, users, service accounts, job token scopes | 2026-09-22 | https://docs.gitlab.com/api/ | `doc/api` in the docs repo | align (fields, identifiers) |
| Audit event streaming | 2026-09-22 | https://docs.gitlab.com/administration/compliance/audit_event_streaming/ | docs repo | adopt |
| GitLab FIPS (development page; the compliance page redirected to a sign-in wall) | 2026-09-22 | https://docs.gitlab.com/development/fips_gitlab/ | docs repo | reference |
| Chainguard GitLab images guide and directory | modified 2026-09-08; read 2026-09-22 | https://edu.chainguard.dev/chainguard/containers/getting-started/platform-and-infrastructure/gitlab/ | images.chainguard.dev directory | reference (image names; CE only) |
| Cartography GitLab module | commit `ed02321a42`, 2026-09-22 | https://github.com/cartography-cncf/cartography (`cartography/models/gitlab/`) | repo releases | align (node names, properties) |
| GitLabHound (Compass Security, BloodHound OpenGraph) | pseudo-version 2026-04-10 | https://pkg.go.dev/github.com/CompassSecurity/gitlabhound | repo commits | align (edges, incident lore) |
| Glato → Trajan (Praetorian) | 2026-09-22 | https://github.com/praetorian-inc/glato | Trajan repo | reference |
| OMGCICD (Pulse Security) | 2023-11-20 | https://pulsesecurity.co.nz/articles/OMGCICD-gitlab | — | incident (privileged runners, deploy keys) |
| GitLab security releases (CVE-2023-7028, -4812, -2825, CVE-2024-5655/-6385) | 2026-09-22 | https://docs.gitlab.com/releases/patches/ | GitLab security release feed | incident |
| GitLab trademark guidelines (logo use) | "last modified 2026-08-27" | https://handbook.gitlab.com/handbook/marketing/brand-and-product-marketing/brand/brand-activation/trademark-guidelines/ | — | decides the icons |

Field lists were read through a summarising fetch, not verbatim; a collector build re-reads each API page
and probes the refused path (build-domain-vocabulary, "Documentation gives you the rule; only a call gives
you the failure shape").
