import re

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultStatus


class BranchCheckPlugin(Plugin):
    _allowed_symbols_regex = re.compile(r"^[-a-zA-Z\d_./#]+$")

    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        if context.log:
            context.log.debug(f"Executing '{cls.__name__}' for ref: '{context.ref.ref}'")

        status = PluginResultStatus.Ok if cls._allowed_symbols_regex.search(context.ref.ref) \
            else PluginResultStatus.Failed

        return PluginResult(status, None)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log:
            return

        log_func = context.log.info if result.status == PluginResultStatus.Ok else context.log.error
        log_func(f"Check '{cls.__name__}' finished with status: '{result.status}'")

        if result.status == PluginResultStatus.Ok:
            return

        context.log.error(f"Invalid symbols in ref/branch name: '{context.ref.ref}', only [a-zA-Z0-9_./#] allowed")
