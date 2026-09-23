"""SSO Provider — A sign-in provider an instance (or a gitlab."""

from typing import Any, ClassVar

from django.db import models
from tap_plugin.gitlab.models._schema import DISPLAY_APPLICATION, PLANE_APPLICATION, validation_schema

from tap_grid.models import BaseModel


class SsoProvider(BaseModel):
    """A sign-in provider an instance (or a gitlab.com group) delegates authentication to: an OmniAuth SAML or
    OpenID Connect provider, or LDAP.

    What the provider trusts is an edge: TRUSTS_ISSUER (identity_core) for an OIDC issuer, TRUSTS_SAML_IDP
    for a SAML identity provider.

    Spec: specs/spec-gitlab-v0.md (req-gitlab-models-application).
    """

    ENTITY_TYPE: ClassVar[str] = "gitlab__sso_provider"
    ENTITY_NAME: ClassVar[str] = "SSO Provider"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A sign-in provider an instance (or a gitlab.com group) delegates authentication to: an OmniAuth SAML or OpenID Connect provider, or LDAP."
    )
    ENTITY_ICON: ClassVar[str] = "gitlab-sso-provider"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = dict(PLANE_APPLICATION)
    # Identity: the fields a design can know. Revisited when the collector observes GitLab's own ids
    # (req-gitlab-collector, Backlog).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("instance_name", "name",)
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = DISPLAY_APPLICATION

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "instance_name": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "protocol": {"type": "string", "enum": ["saml", "openid_connect", "ldap", "other", ""]},
        "label": {"type": "string"},
        "auto_create_users": {"type": ["boolean", "null"]},
        "block_auto_created_users": {"type": ["boolean", "null"]},
        "auto_link_user": {"type": ["boolean", "null"]},
        "enforced": {"type": ["boolean", "null"]},
        "configuration": {"type": "object"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = validation_schema(FIELD_CRUD_SCHEMA)
    CREATE_REQUIRED: ClassVar[list[str]] = ["instance_name", "name"]

    # The owning GitLab instance's name (its natural key). Part of this type's identity: the same path on two
    # instances (staging and production) is two things.
    instance_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The provider's name in gitlab.rb (for example 'saml' or 'openid_connect').
    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # The sign-in protocol.
    protocol = models.CharField(max_length=32, blank=True, default="")
    # The label shown on the sign-in page.
    label = models.CharField(max_length=255, blank=True, default="")
    # Whether a first sign-in creates an account (allow_single_sign_on).
    auto_create_users = models.BooleanField(null=True, blank=True)
    # Whether accounts created by a first sign-in start blocked until an administrator approves them.
    block_auto_created_users = models.BooleanField(null=True, blank=True)
    # Whether a sign-in links to an existing account with the same email.
    auto_link_user = models.BooleanField(null=True, blank=True)
    # Whether this provider is the only way to sign in (password sign-in disabled).
    enforced = models.BooleanField(null=True, blank=True)
    # The source record as read, for facts not promoted to a column.
    configuration = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "gitlab__sso_provider"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
