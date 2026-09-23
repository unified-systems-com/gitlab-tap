"""The posture strip's instance chooser (req-gitlab-panel-posture-5): pure function, no grid."""

from __future__ import annotations

from tap_plugin.gitlab.panels.posture import chooser


def test_chooser_warns_when_a_name_overlaps() -> None:
    """The name filter cannot tell `aba` from `ababa`; the strip says so instead of presenting one instance."""
    assert "ababa" in chooser(["aba", "ababa"], "aba", {})["note"]
    assert chooser(["staging", "production"], "staging", {})["note"] == ""


def test_single_instance_is_the_default() -> None:
    """Blank selects every instance; with one on the grid, the strip names it."""
    assert chooser(["GitLab"], "", {})["label"] == "GitLab"
    assert chooser(["a", "b"], "", {})["label"] == "all instances"
