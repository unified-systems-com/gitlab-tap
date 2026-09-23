"""Shared pieces of the gitlab models: the plane dimension, display defaults, and the one derivation of
each model's validation schema from its CRUD schema (spec-gitlab-v0.md, req-gitlab-models-infrastructure,
req-gitlab-models-application)."""

from typing import Any

#: `gitlab.plane` partitions the vocabulary: the processes a deployment runs (infrastructure) versus the
#: objects GitLab keeps in its database (application). A property of the type, so a default dimension.
PLANE_INFRASTRUCTURE: dict[str, str] = {"gitlab.plane": "infrastructure"}
PLANE_APPLICATION: dict[str, str] = {"gitlab.plane": "application"}

#: Display defaults (tap_viz). Infrastructure in GitLab's orange, application objects in its purple.
DISPLAY_INFRASTRUCTURE: dict[str, Any] = {
    "tap_viz": {
        "shape": "round-rectangle",
        "colors": {"fill": "#FFFFFF", "border": "#E24329", "label": "#7A2A00"},
        "label": {"valign": "bottom", "halign": "center", "position": "outside"},
    }
}
DISPLAY_APPLICATION: dict[str, Any] = {
    "tap_viz": {
        "shape": "round-rectangle",
        "colors": {"fill": "#FFFFFF", "border": "#6B4FBB", "label": "#3B2A70"},
        "label": {"valign": "bottom", "halign": "center", "position": "outside"},
    }
}


def validation_schema(crud: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The model-side validation schema: each CRUD field's JSON Schema, validated before save.

    One derivation, so the API contract and the save-time check cannot disagree.
    """
    return {name: {"validation": "jsonschema", "schema": schema} for name, schema in crud.items()}
