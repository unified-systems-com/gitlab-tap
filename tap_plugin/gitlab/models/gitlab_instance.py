"""GitLab Instance — a GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines."""

from typing import Any, ClassVar

from django.db import models

from tap_grid.models import BaseModel


class GitlabInstance(BaseModel):
    """A GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines.

    v0 is the outer node only: a design can place it before any access exists, so its one
    identifying field stays blank (not observed) until a collector reads it.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-model).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_instance"
    ENTITY_NAME: ClassVar[str] = "GitLab Instance"
    ENTITY_DESCRIPTION: ClassVar[str] = "A GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines."
    ENTITY_ICON: ClassVar[str] = "gitlab-instance"
    # No default dimension: the dcom value belongs to the observation (a seeded design node is
    # `design`, a collected one `configuration`), so the bundle that seeds a node stamps it.
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {}
    # A design-phase node has no observed identifier; its name is the only fact it carries.
    # Revisit when the collector makes base_url observable (req-gitlab-collector).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = {
        "tap_viz": {
            "shape": "round-rectangle",
            "colors": {"fill": "#FFFFFF", "border": "#FC6D26", "label": "#7A2A00"},
            "label": {"valign": "bottom", "halign": "center", "position": "outside"},
        }
    }

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "name": {"type": "string", "minLength": 1},
        "base_url": {"type": "string"},
        "configuration": {"type": "object"},
        "tags": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "name": {"validation": "jsonschema", "schema": {"type": "string", "minLength": 1}},
        "base_url": {"validation": "jsonschema", "schema": {"type": "string"}},
        "configuration": {"validation": "jsonschema", "schema": {"type": "object"}},
        "tags": {"validation": "jsonschema", "schema": {"type": "object"}},
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["name"]

    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The instance's base URL, for example https://gitlab.example.com. Blank until observed.
    base_url = models.CharField(max_length=512, blank=True, default="")
    configuration = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_instance"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
