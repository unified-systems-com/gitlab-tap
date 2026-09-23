"""The /gitlab page, proved against a grid (req-gitlab-page, req-gitlab-panel-posture).

The page bundle and an example deployment (tests/fixtures/example-deployment.grift.json: a small GitLab on
ECS, the shape the spec's reference deployment describes) are imported through `grift_import`, and every
assertion reads back through the page's own searches and the posture panel's own code. What ships is a
claim about the grid, not about a JSON file.

Gryphon reads run on the `search_readonly` alias, a second connection that cannot see an uncommitted
import; `transaction=True` commits, so the reader sees what a reader sees.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
PAGE = json.loads((PACKAGE / "grift" / "gitlab-page.grift.json").read_text())
FIXTURE = json.loads((PACKAGE / "tests" / "fixtures" / "example-deployment.grift.json").read_text())

pytestmark = pytest.mark.django_db(transaction=True, databases=["default", "search_readonly"])


def _nodes(bundle: dict, entity_type: str) -> list[dict]:
    return [n for b in bundle["batches"] for n in b["nodes"] if n["entity"]["entity_type"] == entity_type]


SEARCHES = {n["entity"]["name"]: n["entity"]["entity_id"] for n in _nodes(PAGE, "search")}


@pytest.fixture
def grid() -> None:
    from tap_grid.grift import grift_import

    for bundle in (FIXTURE, PAGE):
        result = grift_import(bundle)
        assert result.success, [e.message for e in result.errors][:5]


def _run(name: str, inputs: dict) -> dict:
    from tap_grid.models import Search
    from tap_grid.search import execute_search

    envelope = execute_search(Search.objects.get(entity_id=SEARCHES[name]), inputs)
    return envelope.get("results", envelope)


def _types(env: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for n in env.get("nodes") or []:
        out[n["entity_type"]] = out.get(n["entity_type"], 0) + 1
    return out


def _edge_type(edge: dict) -> str:
    for holder in (edge, edge.get("data") or {}, edge.get("edge") or {}):
        if holder.get("edge_type"):
            return str(holder["edge_type"])
    raise AssertionError(f"no edge_type in {sorted(edge)}")


def test_every_search_runs_for_all_one_and_no_instance(grid: None) -> None:
    """Every page search executes with the instance blank, named, and unknown; unknown returns nothing."""
    for name in SEARCHES:
        _run(name, {})
        _run(name, {"instance": "GitLab"})
        assert not _run(name, {"instance": "no-such-instance"}).get("nodes"), name


def test_instance_filter_is_exact(grid: None) -> None:
    """A prefix of the instance's name selects nothing (STARTS_WITH and ENDS_WITH together)."""
    assert _run("gitlab — scene: instances", {"instance": "GitLab"})["nodes"]
    assert not _run("gitlab — scene: instances", {"instance": "Git"})["nodes"]


def test_scene_reaches_the_whole_deployment(grid: None) -> None:
    """The scene searches together hold every node of the example deployment except the GitLab ECS
    cluster, which nothing in the vocabulary reaches (aws_core has no cluster-to-service edge)."""
    seen: set[str] = set()
    edge_types: set[str] = set()
    for name in SEARCHES:
        if not name.startswith("gitlab — scene:"):
            continue
        env = _run(name, {})
        seen |= {n["entity_id"] for n in env.get("nodes") or []}
        edge_types |= {_edge_type(e) for e in env.get("edges") or []}
    expected = {n["entity"]["entity_id"] for b in FIXTURE["batches"] for n in b["nodes"] if n["entity"]["name"] != "staging · gitlab"}
    assert expected <= seen, sorted(n["entity"]["name"] for b in FIXTURE["batches"] for n in b["nodes"] if n["entity"]["entity_id"] in expected - seen)
    assert {"RUNS_ON_SERVICE__gitlab", "ROUTES_TRAFFIC__aws_core", "STORES_OBJECTS__gitlab", "TRUSTS_ISSUER__identity_core"} <= edge_types


def test_tables_return_typed_nodes(grid: None) -> None:
    """Envelope mode: the components table receives the six components as nodes."""
    env = _run("gitlab — components of an instance", {"instance": "GitLab"})
    assert _types(env) == {"gitlab__gitlab_component": 6}


def test_posture_tiles_three_states(grid: None) -> None:
    """Populated tiles count; a type the grid holds none of reads not observed, never zero."""
    from tap_plugin.gitlab.panels.posture import answer

    from tap_grid.caller_context import CallerContext
    from tap_grid.services import WriteOperation, write_batch

    write_batch([WriteOperation(verb="create_node", type_slug="gitlab__access_token",
                                payload={"instance_name": "GitLab", "owner_path": "alice", "name": "cli", "expires": False}),
                 # A variable whose protection nobody observed: it must not make the variables tile read clear.
                 WriteOperation(verb="create_node", type_slug="gitlab__ci_variable",
                                payload={"instance_name": "GitLab", "scope": "instance", "key": "DEPLOY_TOKEN"})],
                caller_context=CallerContext())
    posture = next(n for n in _nodes(PAGE, "panel") if n["node"]["slug"] == "gitlab-posture")
    tiles = {t["key"]: t for t in posture["node"]["config"]["tiles"]}
    inputs = {"instance": "GitLab", "cutoff": "2100-01-01T00:00:00Z"}
    state = {key: answer(spec, inputs) for key, spec in tiles.items()}
    assert all(t.state != "error" for t in state.values()), {k: t.error for k, t in state.items() if t.state == "error"}
    # Unobserved deciding facts never read clear: they are counted apart and the tile reads not observed.
    assert (state["variables"].state, state["variables"].unobserved) == ("not_observed", 1)
    assert (state["components"].state, state["components"].unobserved) == ("not_observed", 6)
    assert (state["open-runners"].state, state["open-runners"].unobserved) == ("not_observed", 1)  # access_level unset
    assert state["gitaly-storage"].state == "not_observed"  # the fixture has no volume edge
    # Observed facts answer.
    assert state["privileged"].state == "clear" and state["privileged"].population == 1
    assert state["password-signin"].state == "clear"
    assert state["audit-stream"].state == "finding"  # CE: no audit event streaming
    # A token whose revoked flag was never observed still counts: a null is not "revoked".
    assert state["tokens-never-expire"].state == "finding" and state["tokens-never-expire"].count == 1

