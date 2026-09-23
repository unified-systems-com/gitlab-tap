"""TAP GitLab models."""

from tap_plugin.gitlab.models.access_token import AccessToken
from tap_plugin.gitlab.models.audit_event_destination import AuditEventDestination
from tap_plugin.gitlab.models.ci_variable import CiVariable
from tap_plugin.gitlab.models.deploy_key import DeployKey
from tap_plugin.gitlab.models.deploy_token import DeployToken
from tap_plugin.gitlab.models.gitaly_node import GitalyNode
from tap_plugin.gitlab.models.gitlab_component import GitlabComponent
from tap_plugin.gitlab.models.gitlab_environment import GitlabEnvironment
from tap_plugin.gitlab.models.gitlab_group import GitlabGroup
from tap_plugin.gitlab.models.gitlab_instance import GitlabInstance
from tap_plugin.gitlab.models.gitlab_project import GitlabProject
from tap_plugin.gitlab.models.gitlab_runner import GitlabRunner
from tap_plugin.gitlab.models.gitlab_user import GitlabUser
from tap_plugin.gitlab.models.protected_branch import ProtectedBranch
from tap_plugin.gitlab.models.runner_manager import RunnerManager
from tap_plugin.gitlab.models.sso_provider import SsoProvider

__all__ = [
    "GitlabInstance",
    "GitlabComponent",
    "GitalyNode",
    "RunnerManager",
    "GitlabRunner",
    "GitlabGroup",
    "GitlabProject",
    "GitlabUser",
    "ProtectedBranch",
    "GitlabEnvironment",
    "CiVariable",
    "DeployKey",
    "DeployToken",
    "AccessToken",
    "SsoProvider",
    "AuditEventDestination",
]
