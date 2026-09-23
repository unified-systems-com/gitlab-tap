"""GitLab Runner Manager — One running GitLab Runner process (a runner manager)."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_INFRASTRUCTURE, PLANE_INFRASTRUCTURE, validation_schema

from tap_grid.models import BaseModel


class RunnerManager(BaseModel):
    """One running GitLab Runner process (a runner manager): it authenticates as a registered runner, polls for
    jobs, and launches each job with its executor.

    A runner registration (gitlab__gitlab_runner) can be served by many managers; the manager is the process
    that runs somewhere and holds the executor configuration. It has no free-form configuration field: the
    source records GitLab keeps for it can carry secret material, so only promoted columns are stored.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-infrastructure).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__runner_manager"
    ENTITY_NAME: ClassVar[str] = "GitLab Runner Manager"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "One running GitLab Runner process (a runner manager): it authenticates as a registered runner, polls for jobs, and launches each job with its executor."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-runner-manager"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_INFRASTRUCTURE)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_INFRASTRUCTURE

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "system_id": {"type": "string"},
        "executor": {"type": "string", "enum": ["docker", "docker-autoscaler", "instance", "kubernetes", "shell", "ssh", "custom", "docker+machine", "docker-windows", "virtualbox", "parallels", ""]},
        "custom_driver": {"type": "string"},
        "privileged": {"type": ["boolean", "null"]},
        "concurrent": {"type": ["integer", "null"]},
        "status": {"type": "string", "enum": ["online", "offline", "stale", "never_contacted", ""]},
        "contacted_at": {"type": "string"},
        "platform": {"type": "string"},
        "architecture": {"type": "string"},
        "image": {"type": "string"},
        "version": {"type": "string"},
        "fips_enabled": {"type": ["boolean", "null"]},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The manager's name in its deployment (for example 'staging · runner-manager').
    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The runner manager's system_id as GitLab records it. Blank until observed.
    system_id = models.CharField(max_length=128, blank=True, default="")
    # The executor in config.toml. custom (with a driver) is how the AWS Fargate driver runs jobs.
    executor = models.CharField(max_length=32, blank=True, default="")
    # For the custom executor, the driver it calls (for example 'fargate').
    custom_driver = models.CharField(max_length=64, blank=True, default="")
    # Whether jobs run privileged (docker executors). Read from config.toml; the GitLab API does not expose
    # it.
    privileged = models.BooleanField(null=True, blank=True)
    # The maximum number of jobs this manager runs at once.
    concurrent = models.IntegerField(null=True, blank=True)
    # GitLab's contact status for this manager.
    status = models.CharField(max_length=32, blank=True, default="")
    # When GitLab last heard from the manager (ISO 8601).
    contacted_at = models.CharField(max_length=64, blank=True, default="")
    # The OS the manager reports (for example linux).
    platform = models.CharField(max_length=32, blank=True, default="")
    # The CPU architecture the manager reports (for example amd64).
    architecture = models.CharField(max_length=32, blank=True, default="")
    # The container image reference the process runs from (for example a Chainguard -fips image).
    image = models.CharField(max_length=512, blank=True, default="")
    # The GitLab (or GitLab Runner) version the process reports.
    version = models.CharField(max_length=64, blank=True, default="")
    # Whether the process runs in FIPS mode (a validated crypto provider is in use). Null means not observed.
    fips_enabled = models.BooleanField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__runner_manager"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
