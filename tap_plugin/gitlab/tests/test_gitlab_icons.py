"""Icons (req-gitlab-icons): every type's icon exists, is square and carries an explicit 64px size, and
none is GitLab's trademarked logo."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tap_grid.registry import get_model_class

PACKAGE = Path(__file__).resolve().parents[1]
ICONS = PACKAGE / "static" / "gitlab" / "icons"
TYPES = [
    "gitlab__gitlab_instance", "gitlab__gitlab_component", "gitlab__gitaly_node", "gitlab__runner_manager",
    "gitlab__gitlab_runner", "gitlab__gitlab_group", "gitlab__gitlab_project", "gitlab__gitlab_user",
    "gitlab__protected_branch", "gitlab__gitlab_environment", "gitlab__ci_variable", "gitlab__deploy_key",
    "gitlab__deploy_token", "gitlab__access_token", "gitlab__sso_provider", "gitlab__audit_event_destination",
]


@pytest.mark.parametrize("type_slug", TYPES)
def test_icon_is_square_and_sized(type_slug: str) -> None:
    svg = (ICONS / f"{get_model_class(type_slug).ENTITY_ICON}.svg").read_text()
    assert 'width="64"' in svg and 'height="64"' in svg
    box = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    assert box and box.group(1) == box.group(2)
    assert "<title>GitLab</title>" not in svg, "GitLab's logo is not licensed for reuse; draw a glyph"
