"""Gitaly Node — One Gitaly server."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_INFRASTRUCTURE, PLANE_INFRASTRUCTURE, validation_schema

from tap_grid.models import BaseModel


class GitalyNode(BaseModel):
    """One Gitaly server: the stateful Git RPC service that stores repositories on its local disk and serves
    them to every other component.

    Gitaly is the one GitLab component that holds repository data. GitLab supports only local storage for it
    (block storage such as an attached EBS volume), never NFS or a cloud file system such as EFS.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-infrastructure).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitaly_node"
    ENTITY_NAME: ClassVar[str] = "Gitaly Node"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "One Gitaly server: the stateful Git RPC service that stores repositories on its local disk and serves them to every other component."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-gitaly"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_INFRASTRUCTURE)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_INFRASTRUCTURE

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "storage_names": {"type": ["array", "null"], "items": {"type": "string"}},
        "deployment_mode": {"type": "string", "enum": ["standalone", "praefect_cluster", ""]},
        "image": {"type": "string"},
        "version": {"type": "string"},
        "fips_enabled": {"type": ["boolean", "null"]},
        "health": {"type": "string", "enum": ["healthy", "degraded", "unhealthy", ""]},
        "health_observed_at": {"type": "string"},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The node's name in its deployment (for example 'staging · gitaly-1').
    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The repository storage names this node serves (for example ['default']).
    storage_names = models.JSONField(null=True, blank=True, default=None)
    # standalone (one Gitaly, repositories on one node) or praefect_cluster (Gitaly Cluster behind Praefect).
    deployment_mode = models.CharField(max_length=32, blank=True, default="")
    # The container image reference the process runs from (for example a Chainguard -fips image).
    image = models.CharField(max_length=512, blank=True, default="")
    # The GitLab (or GitLab Runner) version the process reports.
    version = models.CharField(max_length=64, blank=True, default="")
    # Whether the process runs in FIPS mode (a validated crypto provider is in use). Null means not observed.
    fips_enabled = models.BooleanField(null=True, blank=True)
    # Last health verdict (for example the /-/readiness check). Blank means not observed, never healthy.
    health = models.CharField(max_length=32, blank=True, default="")
    # When `health` was observed (ISO 8601). Blank with `health`.
    health_observed_at = models.CharField(max_length=64, blank=True, default="")
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitaly_node"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
