"""Behaviour tests for gitlab__gitlab_instance (req-gitlab-model)."""

from __future__ import annotations

import pytest
from tap_plugin.gitlab.models import GitlabInstance

from tap_grid.caller_context import CallerContext
from tap_grid.services import WriteOperation, write_batch

TYPE = "gitlab__gitlab_instance"


@pytest.mark.django_db
class TestGitlabInstance:
    def test_create_with_name_only(self) -> None:
        """req-gitlab-model-1: a design-phase node needs only its name."""
        result = write_batch(
            [WriteOperation(verb="create_node", type_slug=TYPE, payload={"name": "staging"})],
            caller_context=CallerContext(),
        )
        assert result.results[0].success
        row = GitlabInstance.all_objects.get(entity_id=result.results[0].entity_id)
        assert row.name == "staging"
        assert row.base_url == ""

    def test_name_required(self) -> None:
        """req-gitlab-model-2: a write without a name is refused."""
        result = write_batch(
            [WriteOperation(verb="create_node", type_slug=TYPE, payload={"base_url": "x"})],
            caller_context=CallerContext(),
        )
        assert not result.results[0].success


def test_keyed_by_name() -> None:
    """req-gitlab-model-3: the key rests only on a field the model carries."""
    assert GitlabInstance.NATURAL_KEY == ("name",)
    names = {f.name for f in GitlabInstance._meta.get_fields()}
    assert all(k in names for k in GitlabInstance.NATURAL_KEY)
