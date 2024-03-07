import simplejson

from pathlib import Path

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultStatus


class JsonCheckPlugin(Plugin):
    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        errors = {}

        if context.log:
            context.log.info(f"Executing '{__name__}'")

        diff = context.ref.diff(context.repo)
        for diff_content in diff:
            if diff_content.deleted_file:
                continue

            file_path = Path(context.repo.working_dir) / diff_content.a_path
            if file_path.suffix != ".json":
                continue

            with open(file_path, "r") as file:
                try:
                    simplejson.load(file)
                except ValueError as error:
                    errors[file_path] = error
                    continue

        return PluginResult(PluginResultStatus.Failed, errors) if errors else PluginResult(PluginResultStatus.Ok, None)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log or result.status == PluginResultStatus.Ok:
            return
        for file_path, error in result.data.items():
            context.log.error(f"Check JSON failed for file: '{file_path}' with error: '{error}'")
