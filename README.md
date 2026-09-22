# gitlab-tap

GitLab as grid vocabulary: v0 carries one outer node, the GitLab instance (a self-managed server or gitlab.com), so a design can place it before anything is collected.

## What this plugin owns

One type in v0: `gitlab__gitlab_instance` — a GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines. A design can place it before any access exists; everything inside it is later vocabulary.

## Read first

`specs/spec-gitlab-v0.md` — this is a thin v0 that puts the piece on the board; the full spec interview runs when the plugin grows.

## Stand it up

From a TAP core checkout:

```bash
scripts/spawn-session.sh <label> cli --from 'git+https://github.com/unified-systems-com/gitlab-tap@<rev>#ci' --dev-plugins gitlab
```
