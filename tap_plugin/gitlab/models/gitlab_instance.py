"""GitLab Instance — a GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import validation_schema

from tap_grid.models import BaseModel


class GitlabInstance(BaseModel):
    """A GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines.

    The outer node everything else in the vocabulary belongs to: its components and Gitaly nodes
    (RUNS_COMPONENT), its groups and user accounts, its runners, sign-in providers and audit streams. It
    also carries the instance-wide sign-in posture, because those settings exist once per instance.
    A design can place it before any access exists, so every observed field stays blank (not observed)
    until a collector reads it.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-model).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__gitlab_instance"
    ENTITY_NAME: ClassVar[str] = "GitLab Instance"
    ENTITY_DESCRIPTION: ClassVar[str] = "A GitLab instance: one self-managed GitLab server, or gitlab.com, hosting groups, projects and CI/CD pipelines."
    ENTITY_ICON: ClassVar[str] = "gitlab-instance"
    # No default dimension. The dcom value belongs to the observation (a seeded design node is
    # `design`, a collected one `configuration`), so the bundle that seeds a node stamps it; and the
    # instance straddles both `gitlab.plane` values (it is the deployment and the application), so it
    # carries neither.
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
        "edition": {"type": "string", "enum": ["ce", "ee", ""]},
        "version": {"type": "string"},
        "fips_mode": {"type": ["boolean", "null"]},
        "password_auth_enabled_for_web": {"type": ["boolean", "null"]},
        "password_auth_enabled_for_git": {"type": ["boolean", "null"]},
        "require_two_factor": {"type": ["boolean", "null"]},
        "signup_enabled": {"type": ["boolean", "null"]},
        "configuration": {"type": "object"},
        "tags": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["name"]

    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The instance's base URL, for example https://gitlab.example.com. Blank until observed.
    base_url = models.CharField(max_length=512, blank=True, default="")
    # ce (Community Edition, what the Chainguard images build) or ee (Enterprise Edition). Several objects in
    # this vocabulary exist only on ee tiers (protected environments, audit event streaming).
    edition = models.CharField(max_length=8, blank=True, default="")
    # The GitLab version the instance reports (for example 18.4.1).
    version = models.CharField(max_length=64, blank=True, default="")
    # Whether the instance runs in FIPS mode. Null means not observed.
    fips_mode = models.BooleanField(null=True, blank=True)
    # Whether a password may be used to sign in on the web (false when sign-in goes through SSO only).
    password_auth_enabled_for_web = models.BooleanField(null=True, blank=True)
    # Whether a password may be used for Git over HTTPS.
    password_auth_enabled_for_git = models.BooleanField(null=True, blank=True)
    # Whether every user must enable two-factor authentication.
    require_two_factor = models.BooleanField(null=True, blank=True)
    # Whether anyone may register an account.
    signup_enabled = models.BooleanField(null=True, blank=True)
    configuration = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__gitlab_instance"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
