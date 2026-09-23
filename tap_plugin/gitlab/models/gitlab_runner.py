"""GitLab Runner — A runner registration."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class GitlabRunner(BaseModel):
    """A runner registration: the record GitLab keeps for a runner, which decides whose jobs it may take (its
    scope, tags, whether it runs untagged jobs and whether it runs only protected refs).

    The registration, not the process: the process is gitlab__runner_manager. Scope is instance_type,
    group_type or project_type; an instance runner that runs untagged, unprotected jobs takes anyone's
    pipeline. It has no free-form configuration field: the source records GitLab keeps for it can carry
    secret material, so only promoted columns are stored.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_runner"
    ENTITY_NAME: ClassVar[str] = "GitLab Runner"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A runner registration: the record GitLab keeps for a runner, which decides whose jobs it may take (its scope, tags, whether it runs untagged jobs and whether it runs only protected refs)."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-runner"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "runner_id": {"type": ["integer", "null"]},
        "runner_type": {"type": "string", "enum": ["instance_type", "group_type", "project_type", ""]},
        "tag_list": {"type": ["array", "null"], "items": {"type": "string"}},
        "run_untagged": {"type": ["boolean", "null"]},
        "locked": {"type": ["boolean", "null"]},
        "access_level": {"type": "string", "enum": ["not_protected", "ref_protected", ""]},
        "paused": {"type": ["boolean", "null"]},
        "maximum_timeout": {"type": ["integer", "null"]},
        "status": {"type": "string", "enum": ["online", "offline", "stale", "never_contacted", ""]},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The runner's description (GitLab's display name for it).
    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # GitLab's numeric runner id. Null until observed.
    runner_id = models.BigIntegerField(null=True, blank=True)
    # The runner's scope.
    runner_type = models.CharField(max_length=32, blank=True, default="")
    # The tags a job must carry to be picked up. Null is not observed; [] is none.
    tag_list = models.JSONField(null=True, blank=True, default=None)
    # Whether the runner also takes jobs with no tags.
    run_untagged = models.BooleanField(null=True, blank=True)
    # Whether a project runner is locked to its projects.
    locked = models.BooleanField(null=True, blank=True)
    # ref_protected: the runner takes jobs only from protected branches and tags.
    access_level = models.CharField(max_length=32, blank=True, default="")
    # Whether the runner is paused (takes no jobs).
    paused = models.BooleanField(null=True, blank=True)
    # The runner's maximum job timeout in seconds.
    maximum_timeout = models.IntegerField(null=True, blank=True)
    # GitLab's contact status for the runner.
    status = models.CharField(max_length=32, blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_runner"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
