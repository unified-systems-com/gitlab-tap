"""Behaviour tests for every gitlab node type (req-gitlab-models-infrastructure, req-gitlab-models-application).

Each type is exercised through the service layer: a write with only its required fields succeeds and
carries the `gitlab.plane` default dimension; a write missing a required field is refused; the natural
key rests only on fields the model carries; and the name the grid shows is derived from the key.
"""

from __future__ import annotations

import pytest

from tap_grid.caller_context import CallerContext
from tap_grid.models import Entity
from tap_grid.registry import get_model_class
from tap_grid.services import WriteOperation, write_batch

#: type -> (plane, minimal payload, the name the grid should show)
CASES: dict[str, tuple[str, dict, str]] = {
    "gitlab__gitlab_component": ("infrastructure", {"instance_name": "gl", "name": "webservice"}, "webservice"),
    "gitlab__gitaly_node": ("infrastructure", {"instance_name": "gl", "name": "gitaly-1"}, "gitaly-1"),
    "gitlab__runner_manager": ("infrastructure", {"instance_name": "gl", "name": "runner-manager"}, "runner-manager"),
    "gitlab__gitlab_runner": ("application", {"instance_name": "gl", "name": "fargate"}, "fargate"),
    "gitlab__gitlab_group": ("application", {"instance_name": "gl", "full_path": "platform/infra"}, "platform/infra"),
    "gitlab__gitlab_project": ("application", {"instance_name": "gl", "full_path": "platform/infra/tf"}, "platform/infra/tf"),
    "gitlab__gitlab_user": ("application", {"instance_name": "gl", "username": "alice"}, "alice"),
    "gitlab__protected_branch": ("application", {"instance_name": "gl", "project_path": "a/b", "name": "main"}, "a/b:main"),
    "gitlab__gitlab_environment": ("application", {"instance_name": "gl", "project_path": "a/b", "name": "production"}, "a/b:production"),
    "gitlab__ci_variable": ("application", {"instance_name": "gl", "scope": "project", "scope_path": "a/b", "key": "AWS_ROLE"}, "a/b:AWS_ROLE"),
    "gitlab__deploy_key": ("application", {"instance_name": "gl", "name": "deployer"}, "deployer"),
    "gitlab__deploy_token": ("application", {"instance_name": "gl", "scope_path": "a/b", "name": "registry-pull"}, "a/b:registry-pull"),
    "gitlab__access_token": ("application", {"instance_name": "gl", "owner_path": "alice", "name": "cli"}, "alice:cli"),
    "gitlab__sso_provider": ("application", {"instance_name": "gl", "name": "saml"}, "saml"),
    "gitlab__audit_event_destination": ("application", {"instance_name": "gl", "name": "siem"}, "siem"),
}


def _create(type_slug: str, payload: dict):
    return write_batch([WriteOperation(verb="create_node", type_slug=type_slug, payload=payload)], caller_context=CallerContext()).results[0]


@pytest.mark.django_db
@pytest.mark.parametrize("type_slug", sorted(CASES))
def test_minimal_write_succeeds_with_plane(type_slug: str) -> None:
    """A write with only the required fields lands, stamped with its plane, named from its key."""
    plane, payload, shown = CASES[type_slug]
    result = _create(type_slug, payload)
    assert result.success, result
    entity = Entity.objects.get(id=result.entity_id)
    assert entity.dimensions.get("gitlab.plane") == plane
    assert entity.name == shown


@pytest.mark.django_db
@pytest.mark.parametrize("type_slug", sorted(CASES))
def test_each_required_field_is_required(type_slug: str) -> None:
    """Dropping any one required field refuses the write."""
    _plane, payload, _shown = CASES[type_slug]
    for field in get_model_class(type_slug).CREATE_REQUIRED:
        partial = {k: v for k, v in payload.items() if k != field}
        assert not _create(type_slug, partial).success, f"{type_slug} accepted a write without {field}"


@pytest.mark.parametrize("type_slug", sorted(CASES))
def test_natural_key_rests_on_model_fields(type_slug: str) -> None:
    """Every key field is a column, and the owning instance is part of every key."""
    cls = get_model_class(type_slug)
    names = {f.name for f in cls._meta.get_fields()}
    assert all(k in names for k in cls.NATURAL_KEY)
    assert cls.NATURAL_KEY[0] == "instance_name"


@pytest.mark.django_db
def test_unobserved_booleans_stay_null() -> None:
    """Blank is not observed: a boolean nobody wrote reads null, never false."""
    result = _create("gitlab__ci_variable", {"instance_name": "gl", "scope": "instance", "key": "TOKEN"})
    assert result.success, result
    row = get_model_class("gitlab__ci_variable").all_objects.get(entity_id=result.entity_id)
    assert row.protected is None and row.masked is None


@pytest.mark.django_db
def test_enum_rejects_unknown_value() -> None:
    """A closed vocabulary refuses a word it does not know."""
    assert not _create("gitlab__gitlab_component", {"instance_name": "gl", "name": "x", "component": "nginx"}).success


def test_every_manifest_model_is_covered() -> None:
    """A type added to the manifest without a case here is caught by name."""
    import tomllib
    from pathlib import Path

    manifest = tomllib.loads((Path(__file__).resolve().parents[1] / "tap-plugin.toml").read_text())
    declared = set(manifest["models"]) - {"gitlab__gitlab_instance"}
    assert declared == set(CASES)


#: Every type: a runner manager's config.toml holds its runner token, a variable's record its value, a
#: component's configuration its database password, the instance's settings its keys.
NO_RAW_RECORD = [*sorted(CASES), "gitlab__gitlab_instance"]


@pytest.mark.parametrize("type_slug", NO_RAW_RECORD)
def test_no_type_keeps_a_raw_record(type_slug: str) -> None:
    """GitLab's records can carry secret material, so no type has a free-form field that could hold it."""
    cls = get_model_class(type_slug)
    assert "configuration" not in cls.FIELD_CRUD_SCHEMA
    assert "configuration" not in {f.name for f in cls._meta.get_fields()}
    # `tags` (the instance's labels, set by whoever places it) is the one object field, and is not a source record.
    assert not any(schema.get("type") in ("object", ["object", "null"]) for name, schema in cls.FIELD_CRUD_SCHEMA.items() if name != "tags")


@pytest.mark.django_db
def test_a_value_cannot_be_smuggled_in() -> None:
    """A write carrying the variable's value in an undeclared field is refused."""
    assert not _create("gitlab__ci_variable", {"instance_name": "gl", "scope": "instance", "key": "K", "configuration": {"value": "sentinel"}}).success
    assert not _create("gitlab__ci_variable", {"instance_name": "gl", "scope": "instance", "key": "K", "value": "sentinel"}).success
    assert not _create("gitlab__runner_manager", {"instance_name": "gl", "name": "m", "configuration": {"token": "sentinel"}}).success


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url", "accepted"),
    [
        ("https://siem.example/collector", True),
        ("", True),
        ("https://user:pass@siem.example/hook", False),
        ("https://siem.example/hook?token=sentinel", False),
        ("https://siem.example/hook#token=sentinel", False),
    ],
)
def test_destination_url_carries_no_credential(url: str, accepted: bool) -> None:
    """An audit destination's URL keeps scheme, host and path only: user info, a query or a fragment could carry a token."""
    result = _create("gitlab__audit_event_destination", {"instance_name": "gl", "name": "siem", "destination_url": url})
    assert result.success is accepted
