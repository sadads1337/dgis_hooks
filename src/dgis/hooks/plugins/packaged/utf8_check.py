import codecs

from pathlib import Path

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultStatus


class UTF8CheckPlugin(Plugin):
    _file_extensions_to_check = [".cpp", ".h", ".c", ".hpp", ".hqt", ".json", ".xml", ".txt", ".md"]

    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        errors = {}
        diff = context.ref.diff(context.repo)
        for diff_content in diff:
            if diff_content.deleted_file:
                continue

            file_path = Path(context.repo.working_dir) / diff_content.a_path
            if not file_path.exists():
                continue

            if file_path.suffix.lower() not in cls._file_extensions_to_check:
                continue

            try:
                codecs.open(file_path, encoding='utf-8', errors='strict').readlines()
            except UnicodeDecodeError as error:
                errors["file_path"] = error

        return PluginResult(PluginResultStatus.Failed, errors) if errors else PluginResult(PluginResultStatus.Ok, None)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log or result.status == PluginResultStatus.Ok:
            return
        for file_path, error in result.data.items():
            context.log.error(f"Check JSON failed for file: '{file_path}' with error: '{error}'")
