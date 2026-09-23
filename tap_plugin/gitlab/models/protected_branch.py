"""Protected Branch — A protected-branch rule."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class ProtectedBranch(BaseModel):
    """A protected-branch rule: a branch name or wildcard that only named roles, users, groups or deploy keys
    may push to, merge into, or unprotect.

    Role-based grants are the *_access_levels columns; grants to a specific user, group or deploy key are
    PERMITTED_ON_BRANCH edges.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__protected_branch"
    ENTITY_NAME: ClassVar[str] = "Protected Branch"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A protected-branch rule: a branch name or wildcard that only named roles, users, groups or deploy keys may push to, merge into, or unprotect."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-protected-branch"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "project_path", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "project_path": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "push_access_levels": {"type": ["array", "null"], "items": {"type": "integer"}},
        "merge_access_levels": {"type": ["array", "null"], "items": {"type": "integer"}},
        "unprotect_access_levels": {"type": ["array", "null"], "items": {"type": "integer"}},
        "allow_force_push": {"type": ["boolean", "null"]},
        "code_owner_approval_required": {"type": ["boolean", "null"]},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "project_path", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The full path of the project (or group, for a group-level rule) the rule belongs to.
    project_path = models.CharField(max_length=512, blank=True, default="", db_index=True)
    # The branch name or wildcard the rule protects (for example 'main' or 'release/*').
    name = models.CharField(max_length=255, blank=True, default="")
    # Roles allowed to push: 0 no one, 30 developers, 40 maintainers, 60 administrators.
    push_access_levels = models.JSONField(null=True, blank=True, default=None)
    # Roles allowed to merge (same levels).
    merge_access_levels = models.JSONField(null=True, blank=True, default=None)
    # Roles allowed to unprotect the branch (same levels).
    unprotect_access_levels = models.JSONField(null=True, blank=True, default=None)
    # Whether force-push is allowed to the protected branch.
    allow_force_push = models.BooleanField(null=True, blank=True)
    # Whether pushes and merges need Code Owner approval.
    code_owner_approval_required = models.BooleanField(null=True, blank=True)
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__protected_branch"

    def get_name(self) -> str:
        return f"{self.project_path}:{self.name}"

    def __str__(self) -> str:
        return self.get_name()
