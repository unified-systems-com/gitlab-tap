"""CI/CD Variable — A CI/CD variable defined at instance, group or project level, with the protections that decide which jobs receive it and whether it can appear in a job log."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class CiVariable(BaseModel):
    """A CI/CD variable defined at instance, group or project level, with the protections that decide which
    jobs receive it and whether it can appear in a job log. The value is never stored.

    Identity is the scope, the key and the environment scope: the same key may be defined once per
    environment. It has no free-form configuration field: GitLab's record for it carries secret material, so
    only the promoted columns are stored.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__ci_variable"
    ENTITY_NAME: ClassVar[str] = "CI/CD Variable"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A CI/CD variable defined at instance, group or project level, with the protections that decide which jobs receive it and whether it can appear in a job log. The value is never stored."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-ci-variable"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "scope", "scope_path", "key", "environment_scope",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "scope": {"type": "string", "minLength": 1, "enum": ["instance", "group", "project"]},
        "scope_path": {"type": "string"},
        "key": {"type": "string", "minLength": 1},
        "environment_scope": {"type": "string"},
        "variable_type": {"type": "string", "enum": ["env_var", "file", ""]},
        "protected": {"type": ["boolean", "null"]},
        "masked": {"type": ["boolean", "null"]},
        "hidden": {"type": ["boolean", "null"]},
        "raw": {"type": ["boolean", "null"]},
        "description": {"type": "string"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "scope", "key"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # Where the variable is defined.
    scope = models.CharField(max_length=16, blank=True, default="")
    # The full path of the defining group or project. Empty for an instance-level variable, where the scope
    # says it does not apply.
    scope_path = models.CharField(max_length=512, blank=True, default="", db_index=True)
    # The variable's name.
    key = models.CharField(max_length=255, blank=True, default="")
    # Which environments receive it ('*' for all). Empty for instance variables, which have no environment
    # scope.
    environment_scope = models.CharField(max_length=255, blank=True, default="")
    # Delivered as an environment variable or as a file.
    variable_type = models.CharField(max_length=16, blank=True, default="")
    # Whether only pipelines on protected branches and tags receive it.
    protected = models.BooleanField(null=True, blank=True)
    # Whether GitLab masks the value in job logs.
    masked = models.BooleanField(null=True, blank=True)
    # Whether the value is also hidden in the UI after creation (masked and hidden).
    hidden = models.BooleanField(null=True, blank=True)
    # Whether variable references inside the value are left unexpanded.
    raw = models.BooleanField(null=True, blank=True)
    # The variable's description.
    description = models.TextField(blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "gitlab__ci_variable"

    def get_name(self) -> str:
        return f"{self.scope_path or self.instance_name}:{self.key}"

    def __str__(self) -> str:
        return self.get_name()
