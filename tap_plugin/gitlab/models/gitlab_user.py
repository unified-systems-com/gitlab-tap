"""GitLab User — A GitLab user account."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class GitlabUser(BaseModel):
    """A GitLab user account: a person, a service account, or a bot user behind a group or project access
    token.

    Keyed by username inside its instance. user_type separates humans from service accounts and bots.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_user"
    ENTITY_NAME: ClassVar[str] = "GitLab User"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A GitLab user account: a person, a service account, or a bot user behind a group or project access token."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-user"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "username",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "username": {"type": "string", "minLength": 1},
        "user_id": {"type": ["integer", "null"]},
        "name": {"type": "string"},
        "user_type": {"type": "string"},
        "state": {"type": "string"},
        "is_admin": {"type": ["boolean", "null"]},
        "is_auditor": {"type": ["boolean", "null"]},
        "external": {"type": ["boolean", "null"]},
        "two_factor_enabled": {"type": ["boolean", "null"]},
        "locked": {"type": ["boolean", "null"]},
        "last_sign_in_at": {"type": "string"},
        "last_activity_on": {"type": "string"},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "username"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The account's username.
    username = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # GitLab's numeric user id. Null until observed.
    user_id = models.BigIntegerField(null=True, blank=True)
    # The account's display name.
    name = models.CharField(max_length=255, blank=True, default="")
    # GitLab's user type: human, service_account, project_bot, and GitLab's internal bot types.
    user_type = models.CharField(max_length=64, blank=True, default="")
    # active, blocked, deactivated, banned, or GitLab's other account states.
    state = models.CharField(max_length=32, blank=True, default="")
    # Whether the account is an instance administrator.
    is_admin = models.BooleanField(null=True, blank=True)
    # Whether the account is an auditor (read-only access to everything).
    is_auditor = models.BooleanField(null=True, blank=True)
    # Whether the account is external (sees only what it is explicitly given).
    external = models.BooleanField(null=True, blank=True)
    # Whether the account has two-factor authentication enabled.
    two_factor_enabled = models.BooleanField(null=True, blank=True)
    # Whether the account is locked after failed sign-ins.
    locked = models.BooleanField(null=True, blank=True)
    # When the account last signed in (ISO 8601).
    last_sign_in_at = models.CharField(max_length=64, blank=True, default="")
    # The last day GitLab recorded activity for the account.
    last_activity_on = models.CharField(max_length=32, blank=True, default="")
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_user"

    def get_name(self) -> str:
        return self.username

    def __str__(self) -> str:
        return self.get_name()
