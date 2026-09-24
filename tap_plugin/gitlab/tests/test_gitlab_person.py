"""Person link (req-gitlab-person-link): a GitLab account a person holds resolves to identity_core's human."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from tap_plugin.gitlab.models.gitlab_user import GitlabUser

from tap_grid.caller_context import CallerContext
from tap_grid.models import Edge
from tap_grid.services import WriteOperation, write_batch

HELD = "HELD_BY_HUMAN__identity_core"
HUMAN = "identity_core__human"
PKG = Path(__file__).resolve().parents[1]


def _node(type_slug: str, payload: dict) -> str:
    result = write_batch(
        [WriteOperation(verb="create_node", type_slug=type_slug, payload=payload)], caller_context=CallerContext()
    ).results[0]
    assert result.success, result
    return str(result.entity_id)


def _edge(src: str, dst: str, edge_type: str, properties: dict | None = None):
    payload = {"properties": properties} if properties is not None else {}
    return write_batch(
        [WriteOperation(verb="create_edge", from_target=src, to_target=dst, edge_type=edge_type, payload=payload)],
        caller_context=CallerContext(),
    ).results[0]


def test_person_link_is_declared() -> None:
    """req-gitlab-person-link-1: the user type names the edge and the human, and the edge's owner is a declared
    dependency."""
    declared = {
        (e["type"], n["type"])
        for entry in GitlabUser.OUTBOUND_EDGES
        for e in entry["edges"]
        for n in entry.get("nodes", [])
    }
    assert declared == {(HELD, HUMAN)}
    manifest = tomllib.loads((PKG / "tap-plugin.toml").read_text())
    assert "identity_core" in {d["slug"] for d in manifest.get("depends_on", [])}


@pytest.mark.django_db
def test_account_is_held_by_a_human() -> None:
    """req-gitlab-person-link-2."""
    human = _node(HUMAN, {"handle": "t-0001", "name": "Test Person"})
    user = _node("gitlab__gitlab_user", {"instance_name": "gl", "username": "tperson", "user_type": "human"})
    result = _edge(user, human, HELD, {"matched_on": "operator seed"})
    assert result.success, result
    assert Edge.objects.get(entity_id=result.entity_id).properties == {"matched_on": "operator seed"}
    assert not _edge(user, human, HELD, {"matched_by": "email"}).success


@pytest.mark.django_db
def test_shared_account_is_recorded() -> None:
    """req-gitlab-person-link-3: a login held by two people keeps both edges."""
    first = _node(HUMAN, {"handle": "t-0001"})
    second = _node(HUMAN, {"handle": "t-0002"})
    shared = _node("gitlab__gitlab_user", {"instance_name": "gl", "username": "break-glass"})
    assert _edge(shared, first, HELD, {"matched_on": "operator seed"}).success
    assert _edge(shared, second, HELD, {"matched_on": "operator seed"}).success
    targets = Edge.objects.filter(from_entity_id=shared, edge_type=HELD).values_list("to_entity_id", flat=True)
    assert {str(t) for t in targets} == {first, second}


@pytest.mark.django_db
def test_own_edges_still_permitted() -> None:
    """req-gitlab-person-link-4: declaring OUTBOUND_EDGES adds a permission and removes none."""
    user = _node("gitlab__gitlab_user", {"instance_name": "gl", "username": "tperson"})
    project = _node("gitlab__gitlab_project", {"instance_name": "gl", "full_path": "a/b"})
    provider = _node("gitlab__sso_provider", {"instance_name": "gl", "name": "openid_connect"})
    assert _edge(user, project, "MEMBER_OF_PROJECT__gitlab", {"role": "developer"}).success
    assert _edge(user, provider, "SIGNS_IN_VIA_PROVIDER__gitlab").success
