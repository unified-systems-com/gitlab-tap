"""TAP GitLab plugin AppConfig — the base ready() registers the manifest; this one adds the posture strip
panel type (req-gitlab-panel-posture)."""

from tap_plugins.base import TapPluginConfig


class GitlabConfig(TapPluginConfig):
    def ready(self) -> None:
        super().ready()
        from tap_plugin.gitlab.panels.posture import PosturePanelType

        from tap_web.registry import panel_type_registry

        panel_type_registry.register(PosturePanelType.slug, PosturePanelType)
