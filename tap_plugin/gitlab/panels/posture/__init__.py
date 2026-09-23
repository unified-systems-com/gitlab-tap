"""gitlab-posture — the operator's strip at the top of /gitlab: which instance is shown, then one tile per
posture question (unprotected variables, runners open to anyone, credentials that never expire, …).

Spec: specs/spec-gitlab-v0.md (req-gitlab-panel-posture).

Each tile is declared in the panel instance's config, not here, so a consumer can ask its own questions:

    {"key": "...", "label": "...", "help": "...",
     "population": [... objects whose deciding fact was OBSERVED, e.g. v.data.protected IS NOT NULL ...],
     "finding":    [... the population's bad ones, e.g. v.data.protected = false ...],
     "unobserved": [... objects whose deciding fact was NOT observed, e.g. v.data.protected IS NULL ...],  # optional
     "secondary":  {"label": "not masked", "query": [...]},          # optional
     "tone": "bad_if_any" | "good_if_any"}

Three states, never two. The population counts only objects whose deciding fact was observed, so an object
nobody looked at can never make a tile read clear; the unobserved count says how many were left out. A tile
whose population is empty reads *not observed*. A tile whose query fails renders the failure. Only a
populated, answered tile shows a count.

Reads go through Gryphon (``execute_gryphon_raw``) with two inputs the panel supplies: ``instance`` (the
page's ``?instance=``, the instance's name; blank selects every instance) and ``cutoff`` (now + 30 days, ISO
8601, for expiry questions). A query is handed only the inputs it names.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import urlencode

if TYPE_CHECKING:
    from django.http import HttpRequest

    from tap_web.models import Panel

logger = logging.getLogger(__name__)

#: How far ahead an expiry counts as "soon".
EXPIRY_WINDOW = timedelta(days=30)

INSTANCE_QUERY = "MATCH (i:gitlab__gitlab_instance) RETURN i"

TONES = ("bad_if_any", "good_if_any")


@dataclass
class Tile:
    """One answered (or unanswerable) posture question."""

    key: str
    label: str
    help: str
    state: str  # finding | clear | not_observed | error
    count: int = 0
    population: int = 0
    secondary_label: str = ""
    secondary_count: int | None = None
    unobserved: int | None = None
    error: str = ""


class PosturePanelType:
    """Instance chooser and posture tiles, rendered by the panel's own template."""

    slug: ClassVar[str] = "gitlab-posture"
    label: ClassVar[str] = "GitLab posture strip"
    view: ClassVar[str] = "gitlab/panels/posture.html"
    css: ClassVar[list[str]] = ["gitlab/css/posture.css"]
    js: ClassVar[list[str]] = []
    editor_view: ClassVar[str] = ""
    config_defaults: ClassVar[dict[str, Any]] = {"tiles": []}

    @classmethod
    def get_view_context(cls, panel: Panel, request: HttpRequest) -> dict[str, Any]:
        config = dict(cls.config_defaults)
        config.update(panel.config or {})
        selected = str(request.GET.get("instance", "") or "")
        inputs = {"instance": selected, "cutoff": (datetime.now(UTC) + EXPIRY_WINDOW).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            instances = _names(_run(INSTANCE_QUERY, {}))
        except Exception:  # noqa: BLE001 — the panel renders its failure, never a blank frame
            logger.exception("[7c1e] gitlab posture: instance read failed for panel %s", panel.entity_id)
            return {"strip_error": "The instance list could not be read — see the server log ([7c1e]).", "tiles": []}
        return {
            "strip_error": None,
            "chooser": chooser(instances, selected, request.GET),
            "selected": selected,
            "tiles": [answer(tile, inputs) for tile in config.get("tiles") or []],
        }


def chooser(instances: list[str], selected: str, params: Any) -> dict[str, Any]:
    """The instance links. Blank selects every instance, which is the single instance when there is one."""
    options = []
    for name in instances:
        try:
            query = params.copy()
            query["instance"] = name
            href = "?" + query.urlencode()
        except AttributeError:
            href = "?" + urlencode({"instance": name})
        options.append({"name": name, "href": href, "active": name == selected})
    note = ""
    if selected and selected not in instances:
        note = f"No instance named “{selected[:60]}” is on the grid; every tile below reads not observed."
    # The page's searches select by instance_name STARTS_WITH and ENDS_WITH the name (Gryphon has no
    # param-absent predicate yet, tap#360), which also matches a longer name that begins and ends with it.
    overlap = [n for n in instances if selected and n != selected and n.startswith(selected) and n.endswith(selected)]
    if overlap:
        note = (f"The page's tables and tiles also include {', '.join(overlap)}: its name begins and ends with "
                f"“{selected[:60]}”, and the page cannot yet tell them apart.")
    if not selected:
        label = instances[0] if len(instances) == 1 else ("all instances" if instances else "no instance on the grid")
    else:
        label = selected
    return {"options": options, "label": label, "note": note, "all_href": "?" + _without(params, "instance")}


def answer(spec: dict[str, Any], inputs: dict[str, str]) -> Tile:
    """Run one tile's population, finding and secondary queries."""
    tile = Tile(key=str(spec.get("key", "")), label=str(spec.get("label", "")), help=str(spec.get("help", "")), state="error")
    tone = spec.get("tone", "bad_if_any")
    try:
        if spec.get("unobserved"):
            tile.unobserved = _count(spec["unobserved"], inputs)
        tile.population = _count(spec["population"], inputs)
        if tile.population == 0:
            tile.state = "not_observed"
            return tile
        tile.count = _count(spec["finding"], inputs)
        if tone not in TONES:
            raise ValueError(f"unknown tone {tone!r}")
        found = tile.count > 0
        tile.state = ("finding" if found else "clear") if tone == "bad_if_any" else ("clear" if found else "finding")
        secondary = spec.get("secondary")
        if secondary:
            tile.secondary_label = str(secondary.get("label", ""))
            tile.secondary_count = _count(secondary["query"], inputs)
    except Exception as exc:  # noqa: BLE001 — one failed tile must not blank the strip
        logger.exception("[7c1f] gitlab posture tile %s failed: %s", tile.key, exc)
        tile.state = "error"
        tile.error = "The query failed; see the server log ([7c1f])."
    return tile


def _count(query: list[str] | str, inputs: dict[str, str]) -> int:
    text = " ".join(query) if isinstance(query, list) else str(query)
    env = _run(text, {k: v for k, v in inputs.items() if f"${k}" in text})
    return len(env.get("nodes") or [])


def _run(query: str, inputs: dict[str, str]) -> dict[str, Any]:
    from tap_grid.gryphon.executor import execute_gryphon_raw

    return execute_gryphon_raw(query, inputs, layer="full")


def _names(env: dict[str, Any]) -> list[str]:
    names = []
    for node in env.get("nodes") or []:
        data = node.get("data") or {}
        name = data.get("name") or node.get("name") or ""
        if name:
            names.append(str(name))
    return sorted(set(names))


def _without(params: Any, key: str) -> str:
    try:
        query = params.copy()
        query.pop(key, None)
        return query.urlencode()
    except AttributeError:
        return ""
