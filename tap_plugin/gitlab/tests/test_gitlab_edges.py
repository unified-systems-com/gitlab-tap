"""The edge vocabulary (req-gitlab-edges-infrastructure, req-gitlab-edges-application).

File-level checks need no database: every declared edge names only types this plugin owns (an open end
is omitted, never a closed list of another plugin's types), forbids undeclared properties, and stamps
its plane. The service-layer checks prove the schema is enforced: a required property is required and
an unknown one refused.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from tap_grid.caller_context import CallerContext
from tap_grid.exceptions import EdgePropertyValidationError, ServiceValidationError
from tap_grid.services import WriteOperation, create_edge, resolve_entity, write_batch

PACKAGE = Path(__file__).resolve().parents[1]
MANIFEST = tomllib.loads((PACKAGE / "tap-plugin.toml").read_text())
EDGES = {slug: json.loads((PACKAGE / rel).read_text()) for slug, rel in MANIFEST["edges"].items()}


@pytest.mark.parametrize("slug", sorted(EDGES))
def test_endpoints_are_own_types_or_open(slug: str) -> None:
    doc = EDGES[slug]
    assert doc["slug"] == slug
    for side in ("sources", "targets"):
        for t in doc.get(side) or []:
            assert t.startswith("gitlab__"), f"{slug} names foreign type {t}; leave that side open instead"
    if "targets" not in doc:
        assert "open" in doc["description"], f"{slug} leaves its target open without saying so"


@pytest.mark.parametrize("slug", sorted(EDGES))
def test_properties_are_closed_and_plane_stamped(slug: str) -> None:
    doc = EDGES[slug]
    if "property_schema" in doc:
        assert doc["property_schema"].get("additionalProperties") is False
    assert doc["default_dimensions"].get("gitlab.plane") in {"infrastructure", "application"}


def _node(type_slug: str, payload: dict):
    result = write_batch([WriteOperation(verb="create_node", type_slug=type_slug, payload=payload)], caller_context=CallerContext()).results[0]
    assert result.success, result
    return resolve_entity(result.entity_id)


@pytest.mark.django_db
def test_required_property_enforced_and_unknown_refused() -> None:
    project = _node("gitlab__gitlab_project", {"instance_name": "gl", "full_path": "a/b"})
    key = _node("gitlab__deploy_key", {"instance_name": "gl", "name": "deployer"})
    with pytest.raises((EdgePropertyValidationError, ServiceValidationError)):
        create_edge(project, key, "ENABLES_DEPLOY_KEY__gitlab", properties={})
    with pytest.raises((EdgePropertyValidationError, ServiceValidationError)):
        create_edge(project, key, "ENABLES_DEPLOY_KEY__gitlab", properties={"can_push": True, "note": "x"})
    edge = create_edge(project, key, "ENABLES_DEPLOY_KEY__gitlab", properties={"can_push": True})
    assert edge is not None


@pytest.mark.django_db
def test_open_end_accepts_a_foreign_type() -> None:
    """RUNS_ON_SERVICE leaves its target open: an aws_core ECS service is accepted."""
    component = _node("gitlab__gitlab_component", {"instance_name": "gl", "name": "webservice"})
    service = _node("aws_core__aws_ecs_service", {"name": "gitlab-webservice"})
    assert create_edge(component, service, "RUNS_ON_SERVICE__gitlab", properties={"container_name": "webservice"}) is not None

