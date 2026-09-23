"""Access Token — A GitLab access token."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class AccessToken(BaseModel):
    """A GitLab access token: a personal, group, project or impersonation token, with its scopes, role and
    expiry. The secret is never stored.

    The user the token authenticates as (the owner, or the bot user behind a group or project token) is
    AUTHENTICATES_AS_USER. It has no free-form configuration field: the source records GitLab keeps for it
    can carry secret material, so only promoted columns are stored.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__access_token"
    ENTITY_NAME: ClassVar[str] = "Access Token"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A GitLab access token: a personal, group, project or impersonation token, with its scopes, role and expiry. The secret is never stored."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-access-token"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "owner_path", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "owner_path": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "token_type": {"type": "string", "enum": ["personal", "impersonation", "group", "project", ""]},
        "token_id": {"type": ["integer", "null"]},
        "scopes": {"type": ["array", "null"], "items": {"type": "string"}},
        "access_level": {"type": ["integer", "null"]},
        "expires": {"type": ["boolean", "null"]},
        "expires_at": {"type": "string"},
        "active": {"type": ["boolean", "null"]},
        "revoked": {"type": ["boolean", "null"]},
        "last_used_at": {"type": "string"},
        "created_at": {"type": "string"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "owner_path", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The username (personal, impersonation) or group/project full path the token belongs to.
    owner_path = models.CharField(max_length=512, blank=True, default="", db_index=True)
    # The token's name.
    name = models.CharField(max_length=255, blank=True, default="")
    # What kind of token this is.
    token_type = models.CharField(max_length=16, blank=True, default="")
    # GitLab's numeric token id. Null until observed.
    token_id = models.BigIntegerField(null=True, blank=True)
    # api, read_api, read_repository, write_repository, read_registry, …
    scopes = models.JSONField(null=True, blank=True, default=None)
    # For group and project tokens, the role the bot user holds (10-50).
    access_level = models.IntegerField(null=True, blank=True)
    # Whether the credential has an expiry at all. False is the finding (it never expires); null means not
    # observed.
    expires = models.BooleanField(null=True, blank=True)
    # When the token expires (ISO 8601). Blank when it never expires (expires is false) or was not observed.
    expires_at = models.CharField(max_length=64, blank=True, default="")
    # Whether the token is usable (not expired, not revoked).
    active = models.BooleanField(null=True, blank=True)
    # Whether the token has been revoked.
    revoked = models.BooleanField(null=True, blank=True)
    # When the token was last used (ISO 8601).
    last_used_at = models.CharField(max_length=64, blank=True, default="")
    # When the token was created (ISO 8601).
    created_at = models.CharField(max_length=64, blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "gitlab__access_token"

    def get_name(self) -> str:
        return f"{self.owner_path}:{self.name}"

    def __str__(self) -> str:
        return self.get_name()
