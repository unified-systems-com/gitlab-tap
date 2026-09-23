"""Deploy Key — An SSH deploy key."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class DeployKey(BaseModel):
    """An SSH deploy key: a public key that can read (and, where a project grants it, write) project
    repositories without a user account.

    One key can be enabled on many projects; whether it may push is per project, on ENABLES_DEPLOY_KEY. It
    has no free-form configuration field: GitLab's record for it carries secret material, so only the
    promoted columns are stored.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__deploy_key"
    ENTITY_NAME: ClassVar[str] = "Deploy Key"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "An SSH deploy key: a public key that can read (and, where a project grants it, write) project repositories without a user account."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-deploy-key"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "deploy_key_id": {"type": ["integer", "null"]},
        "fingerprint_sha256": {"type": "string"},
        "expires": {"type": ["boolean", "null"]},
        "expires_at": {"type": "string"},
        "created_at": {"type": "string"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The key's title.
    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # GitLab's numeric deploy key id. Null until observed.
    deploy_key_id = models.BigIntegerField(null=True, blank=True)
    # The key's SHA256 fingerprint (the MD5 fingerprint is unavailable in FIPS mode).
    fingerprint_sha256 = models.CharField(max_length=128, blank=True, default="")
    # Whether the credential has an expiry at all. False is the finding (it never expires); null means not
    # observed.
    expires = models.BooleanField(null=True, blank=True)
    # When the key expires (ISO 8601). Blank when it never expires (expires is false) or was not observed.
    expires_at = models.CharField(max_length=64, blank=True, default="")
    # When the key was added (ISO 8601).
    created_at = models.CharField(max_length=64, blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "gitlab__deploy_key"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
