"""GitLab Component — One stateless GitLab service process as deployed."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_INFRASTRUCTURE, PLANE_INFRASTRUCTURE, validation_schema

from tap_grid.models import BaseModel


class GitlabComponent(BaseModel):
    """One stateless GitLab service process as deployed: webservice (Puma), Workhorse, Sidekiq, GitLab Shell,
    the container registry, KAS, Pages, Mailroom, the exporter, or the toolbox/migrations task.

    A GitLab component is one of the processes the cloud-native split runs in containers. Gitaly is not one:
    it is stateful and has its own type (gitlab__gitaly_node). It has no free-form configuration field: the
    source records GitLab keeps for it can carry secret material, so only promoted columns are stored.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-infrastructure).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_component"
    ENTITY_NAME: ClassVar[str] = "GitLab Component"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "One stateless GitLab service process as deployed: webservice (Puma), Workhorse, Sidekiq, GitLab Shell, the container registry, KAS, Pages, Mailroom, the exporter, or the toolbox/migrations task."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-component"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_INFRASTRUCTURE)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_INFRASTRUCTURE

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "component": {"type": "string", "enum": ["webservice", "workhorse", "sidekiq", "gitlab_shell", "registry", "kas", "pages", "mailroom", "exporter", "toolbox", "migrations", ""]},
        "image": {"type": "string"},
        "version": {"type": "string"},
        "fips_enabled": {"type": ["boolean", "null"]},
        "ports": {"type": ["array", "null"], "items": {"type": "integer"}},
        "health_check": {"type": "string"},
        "health": {"type": "string", "enum": ["healthy", "degraded", "unhealthy", ""]},
        "health_observed_at": {"type": "string"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The component's name in its deployment (for example 'staging · webservice').
    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # Which GitLab component this is (the Helm chart's names; webservice is Puma, workhorse its HTTP front).
    component = models.CharField(max_length=32, blank=True, default="")
    # The container image reference the process runs from (for example a Chainguard -fips image).
    image = models.CharField(max_length=512, blank=True, default="")
    # The GitLab (or GitLab Runner) version the process reports.
    version = models.CharField(max_length=64, blank=True, default="")
    # Whether the process runs in FIPS mode (a validated crypto provider is in use). Null means not observed.
    fips_enabled = models.BooleanField(null=True, blank=True)
    # The TCP ports the process listens on (Workhorse 8181, Puma 8080, gitlab-sshd 2222, registry 5000, KAS
    # 8150-8155).
    ports = models.JSONField(null=True, blank=True, default=None)
    # What the health verdict is read from (for example GET /-/readiness).
    health_check = models.CharField(max_length=255, blank=True, default="")
    # Last health verdict (for example the /-/readiness check). Blank means not observed, never healthy.
    health = models.CharField(max_length=32, blank=True, default="")
    # When `health` was observed (ISO 8601). Blank with `health`.
    health_observed_at = models.CharField(max_length=64, blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_component"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
