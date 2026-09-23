"""GitLab Group — A GitLab group (or subgroup)."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class GitlabGroup(BaseModel):
    """A GitLab group (or subgroup): a namespace that holds projects and subgroups and whose members inherit
    access to everything beneath it.

    Keyed by full path inside its instance. Parentage is the NESTS_SUBGROUP edge, not a field. It has no
    free-form configuration field: the source records GitLab keeps for it can carry secret material, so only
    promoted columns are stored.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_group"
    ENTITY_NAME: ClassVar[str] = "GitLab Group"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A GitLab group (or subgroup): a namespace that holds projects and subgroups and whose members inherit access to everything beneath it."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-group"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "full_path",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "full_path": {"type": "string", "minLength": 1},
        "group_id": {"type": ["integer", "null"]},
        "name": {"type": "string"},
        "visibility": {"type": "string", "enum": ["private", "internal", "public", ""]},
        "require_two_factor": {"type": ["boolean", "null"]},
        "two_factor_grace_period": {"type": ["integer", "null"]},
        "shared_runners_enabled": {"type": ["boolean", "null"]},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "full_path"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The group's full path (for example 'platform/infra').
    full_path = models.CharField(max_length=512, blank=True, default="", db_index=True)
    # GitLab's numeric group id. Null until observed.
    group_id = models.BigIntegerField(null=True, blank=True)
    # The group's display name.
    name = models.CharField(max_length=255, blank=True, default="")
    # Who can see the group.
    visibility = models.CharField(max_length=16, blank=True, default="")
    # Whether the group requires two-factor authentication of its members.
    require_two_factor = models.BooleanField(null=True, blank=True)
    # Hours a member may go without 2FA once it is required.
    two_factor_grace_period = models.IntegerField(null=True, blank=True)
    # Whether instance runners may take this group's jobs.
    shared_runners_enabled = models.BooleanField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_group"

    def get_name(self) -> str:
        return self.full_path

    def __str__(self) -> str:
        return self.get_name()
