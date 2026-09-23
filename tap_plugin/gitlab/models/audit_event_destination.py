"""Audit Event Destination — An audit event streaming destination."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class AuditEventDestination(BaseModel):
    """An audit event streaming destination: where an instance or top-level group sends every audit event as it
    happens (an HTTP endpoint, an AWS S3 bucket, or Google Cloud Logging). Ultimate only.

    Where the events land is DELIVERS_EVENTS; which instance or group streams them is STREAMS_AUDIT_EVENTS.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__audit_event_destination"
    ENTITY_NAME: ClassVar[str] = "Audit Event Destination"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "An audit event streaming destination: where an instance or top-level group sends every audit event as it happens (an HTTP endpoint, an AWS S3 bucket, or Google Cloud Logging). Ultimate only."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-audit-destination"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "destination_type": {"type": "string", "enum": ["http", "aws_s3", "google_cloud_logging", ""]},
        "scope": {"type": "string", "enum": ["instance", "group", ""]},
        "destination_url": {"type": "string"},
        "active": {"type": ["boolean", "null"]},
        "event_type_filters": {"type": ["array", "null"], "items": {"type": "string"}},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The destination's name.
    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The kind of destination.
    destination_type = models.CharField(max_length=32, blank=True, default="")
    # Whether the instance or a top-level group streams to it.
    scope = models.CharField(max_length=16, blank=True, default="")
    # For an HTTP destination, the endpoint URL.
    destination_url = models.CharField(max_length=1024, blank=True, default="")
    # Whether streaming to the destination is active.
    active = models.BooleanField(null=True, blank=True)
    # The event types streamed. Null is not observed; [] means all.
    event_type_filters = models.JSONField(null=True, blank=True, default=None)
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__audit_event_destination"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
