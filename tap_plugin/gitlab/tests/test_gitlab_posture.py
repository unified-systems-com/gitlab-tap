"""The posture strip's instance chooser (req-gitlab-panel-posture-5): pure function, no grid."""

from __future__ import annotations

from tap_plugin.gitlab.panels.posture import chooser


def test_chooser_has_no_overlap_note() -> None:
    """The name filter is exact, so `aba` beside `ababa` is one instance and needs no warning."""
    assert chooser(["aba", "ababa"], "aba", {})["note"] == ""
    assert chooser(["staging", "production"], "staging", {})["note"] == ""


def test_single_instance_is_the_default() -> None:
    """Absent selects every instance; with one on the grid, the strip names it."""
    assert chooser(["GitLab"], None, {})["label"] == "GitLab"
    assert chooser(["a", "b"], None, {})["label"] == "all instances"


def test_blank_instance_is_a_value() -> None:
    """A blank ?instance= names no instance, as it does for the page's searches: the strip says so rather
    than counting every instance above tables that show none."""
    blank = chooser(["GitLab"], "", {})
    assert blank["label"] == "" and "No instance named" in blank["note"]
