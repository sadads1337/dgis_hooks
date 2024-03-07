from pathlib import Path

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultStatus


class UTF8CheckPlugin(Plugin):
    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        diff = context.ref.diff(context.repo)
        for diff_content in diff:
            if diff_content.deleted_file:
                continue

            file_path = Path(context.repo.working_dir) / diff_content.a_path
            if not file_path.exists():
                continue

            if file_path.suffix.lower() not in [".cpp", ".h", ".c", ".hpp", ".hqt", ".json", ".xml", ".txt", ".md"]:
                continue

            with open(file_path, mode="rb") as file:
                # TODO check UTF-8
                pass

        return PluginResult(PluginResultStatus.Ok, None)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        assert result.status == PluginResultStatus.Ok
        pass
