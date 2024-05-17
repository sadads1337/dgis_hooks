import io

from pathlib import Path
from xml.etree import ElementTree

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultStatus


class XmlCheckPlugin(Plugin):
    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        errors = {}

        diff = context.ref.diff(context.repo)
        for diff_content in diff:
            if diff_content.deleted_file:
                continue

            if diff_content.renamed_file and not diff_content.b_blob:
                continue

            file_path = Path(context.repo.working_dir) / diff_content.b_path
            if file_path.suffix != ".xml":
                continue

            if context.log:
                context.log.debug(f"Executing '{cls.__name__}' for file: '{file_path}'")

            xml_content = context.repo.git.cat_file("blob", diff_content.b_blob.hexsha).encode()
            file = io.BytesIO(xml_content)
            try:
                ElementTree.parse(file).getroot()
            except ElementTree.ParseError as error:
                errors[file_path] = error

        return PluginResult(PluginResultStatus.Failed if errors else PluginResultStatus.Ok, errors)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log:
            return

        log_func = context.log.info if result.status == PluginResultStatus.Ok else context.log.error
        log_func(f"Check '{cls.__name__}' finished with status: '{result.status}'")

        if result.status == PluginResultStatus.Ok:
            return

        if result.data:
            for file_path, error in result.data.items():
                context.log.error(f"Check XML failed for file: '{file_path}' with error: '{error}'")
