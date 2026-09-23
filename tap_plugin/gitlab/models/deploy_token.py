"""Deploy Token — A deploy token."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class DeployToken(BaseModel):
    """A deploy token: a username and token pair minted on a group or project for reading repositories and
    reading or writing its registries.

    Scoped to the group or project that issued it.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__deploy_token"
    ENTITY_NAME: ClassVar[str] = "Deploy Token"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A deploy token: a username and token pair minted on a group or project for reading repositories and reading or writing its registries."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-deploy-token"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "scope_path", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "scope_path": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "deploy_token_id": {"type": ["integer", "null"]},
        "username": {"type": "string"},
        "scopes": {"type": ["array", "null"], "items": {"type": "string"}},
        "expires": {"type": ["boolean", "null"]},
        "expires_at": {"type": "string"},
        "revoked": {"type": ["boolean", "null"]},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "scope_path", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The full path of the group or project that issued the token.
    scope_path = models.CharField(max_length=512, blank=True, default="", db_index=True)
    # The token's name.
    name = models.CharField(max_length=255, blank=True, default="")
    # GitLab's numeric deploy token id. Null until observed.
    deploy_token_id = models.BigIntegerField(null=True, blank=True)
    # The username the token authenticates as.
    username = models.CharField(max_length=255, blank=True, default="")
    # read_repository, read_registry, write_registry, read_package_registry, write_package_registry, …
    scopes = models.JSONField(null=True, blank=True, default=None)
    # Whether the credential has an expiry at all. False is the finding (it never expires); null means not
    # observed.
    expires = models.BooleanField(null=True, blank=True)
    # When the token expires (ISO 8601). Blank when it never expires (expires is false) or was not observed.
    expires_at = models.CharField(max_length=64, blank=True, default="")
    # Whether the token has been revoked.
    revoked = models.BooleanField(null=True, blank=True)
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__deploy_token"

    def get_name(self) -> str:
        return f"{self.scope_path}:{self.name}"

    def __str__(self) -> str:
        return self.get_name()
