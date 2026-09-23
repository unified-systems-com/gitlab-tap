# gitlab-tap

GitLab as grid vocabulary: a small self-managed GitLab as it is deployed, and the objects inside it that a
FedRAMP 20x operator governs, with a `/gitlab` page per instance.

## What this plugin owns

- **Infrastructure types** — `gitlab__gitlab_component` (webservice, Workhorse, Sidekiq, GitLab Shell,
  registry, …), `gitlab__gitaly_node`, `gitlab__runner_manager` — and the edges saying what each runs on,
  queries, calls, stores to and reads. The platform end of those edges is left open, so an ECS service, an
  RDS instance or an S3 bucket from `aws_core` sits there without this plugin naming AWS.
- **Application types** — instance, groups, projects, accounts, runner registrations, protected branches and
  environments, CI/CD variables, deploy keys and tokens, access tokens, sign-in providers, audit event
  destinations — and the membership, grant, credential, sign-in and audit edges between them.
- **The `/gitlab` page** — the deployment drawn as one picture (a reusable layout module), a posture strip
  (three states: a count, clear, or not observed), and the tables an assessor asks for. `?instance=<name>`
  picks the instance.

## Read first

`specs/spec-gitlab-v0.md` (the requirements) and `specs/corpus-gitlab.md` (why each type and edge exists,
what was rejected, and the pinned sources).

## Stand it up

From a TAP core checkout:

```bash
scripts/spawn-session.sh <label> cli --from 'git+https://github.com/unified-systems-com/gitlab-tap@<rev>#ci' --dev-plugins gitlab
```
