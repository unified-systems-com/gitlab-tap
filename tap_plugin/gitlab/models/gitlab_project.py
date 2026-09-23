"""GitLab Project — A GitLab project."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class GitlabProject(BaseModel):
    """A GitLab project: one Git repository with its issues, merge requests, CI/CD pipelines, environments and
    settings.

    Keyed by path with namespace inside its instance. The repository's bytes live on a Gitaly node
    (RESIDES_ON_GITALY).

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_project"
    ENTITY_NAME: ClassVar[str] = "GitLab Project"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A GitLab project: one Git repository with its issues, merge requests, CI/CD pipelines, environments and settings."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-project"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "full_path",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "full_path": {"type": "string", "minLength": 1},
        "project_id": {"type": ["integer", "null"]},
        "name": {"type": "string"},
        "visibility": {"type": "string", "enum": ["private", "internal", "public", ""]},
        "default_branch": {"type": "string"},
        "archived": {"type": ["boolean", "null"]},
        "shared_runners_enabled": {"type": ["boolean", "null"]},
        "job_token_inbound_enabled": {"type": ["boolean", "null"]},
        "fork_pipelines_in_parent": {"type": ["boolean", "null"]},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "full_path"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The project's path with namespace (for example 'platform/infra/terraform').
    full_path = models.CharField(max_length=512, blank=True, default="", db_index=True)
    # GitLab's numeric project id. Null until observed.
    project_id = models.BigIntegerField(null=True, blank=True)
    # The project's display name.
    name = models.CharField(max_length=255, blank=True, default="")
    # Who can see the project.
    visibility = models.CharField(max_length=16, blank=True, default="")
    # The project's default branch.
    default_branch = models.CharField(max_length=255, blank=True, default="")
    # Whether the project is archived (read-only).
    archived = models.BooleanField(null=True, blank=True)
    # Whether instance runners may take this project's jobs.
    shared_runners_enabled = models.BooleanField(null=True, blank=True)
    # Whether the CI_JOB_TOKEN inbound allowlist is enforced. False means any project's job token may reach
    # this one.
    job_token_inbound_enabled = models.BooleanField(null=True, blank=True)
    # Whether fork merge-request pipelines may run in this project, with this project's variables and runners.
    fork_pipelines_in_parent = models.BooleanField(null=True, blank=True)
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_project"

    def get_name(self) -> str:
        return self.full_path

    def __str__(self) -> str:
        return self.get_name()
