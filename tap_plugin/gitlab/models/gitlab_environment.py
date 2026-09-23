"""GitLab Environment — A GitLab deployment environment of a project (production, staging, …) and its protection."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class GitlabEnvironment(BaseModel):
    """A GitLab deployment environment of a project (production, staging, …) and its protection: who may deploy
    to it and how many approvals a deployment needs.

    GitLab's own environment object, not TAP's deployment.environment dimension; a protected environment is
    the same object with protection fields set.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_environment"
    ENTITY_NAME: ClassVar[str] = "GitLab Environment"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A GitLab deployment environment of a project (production, staging, …) and its protection: who may deploy to it and how many approvals a deployment needs."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-environment"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "project_path", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "project_path": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "tier": {"type": "string", "enum": ["production", "staging", "testing", "development", "other", ""]},
        "external_url": {"type": "string"},
        "state": {"type": "string"},
        "protected": {"type": ["boolean", "null"]},
        "required_approval_count": {"type": ["integer", "null"]},
        "deploy_access_levels": {"type": ["array", "null"], "items": {"type": "integer"}},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "project_path", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The full path of the project the environment belongs to.
    project_path = models.CharField(max_length=512, blank=True, default="", db_index=True)
    # The environment's name (for example 'production').
    name = models.CharField(max_length=255, blank=True, default="")
    # GitLab's deployment tier.
    tier = models.CharField(max_length=16, blank=True, default="")
    # The environment's URL.
    external_url = models.CharField(max_length=512, blank=True, default="")
    # available, stopping or stopped.
    state = models.CharField(max_length=32, blank=True, default="")
    # Whether the environment is protected (Premium and up).
    protected = models.BooleanField(null=True, blank=True)
    # How many approvals a deployment needs.
    required_approval_count = models.IntegerField(null=True, blank=True)
    # Roles allowed to deploy (30, 40, 60). Named users and groups are edges.
    deploy_access_levels = models.JSONField(null=True, blank=True, default=None)
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_environment"

    def get_name(self) -> str:
        return f"{self.project_path}:{self.name}"

    def __str__(self) -> str:
        return self.get_name()
