import re

from dgis.hooks.plugins.plugin import Plugin, PluginContext, PluginResult, PluginResultPayload, PluginResultStatus
from dgis.hooks.utility.git import RefStatus


class BranchCheckPlugin(Plugin):
    _allowed_symbols_regex = re.compile(r"^[-a-zA-Z\d_./#]+$")

    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        if context.log:
            context.log.debug(f"Executing '{cls.__name__}' for ref: '{context.ref.ref}'")

        if context.ref.status(context.repo) == RefStatus.Deleted:
            return PluginResult(PluginResultStatus.Ok, None)

        status = (
            PluginResultStatus.Ok if cls._allowed_symbols_regex.search(context.ref.ref) else PluginResultStatus.Failed
        )

        if status == PluginResultStatus.Failed:
            stdout = f"Invalid symbols in ref/branch name: '{context.ref.ref}', only [a-zA-Z0-9_./#] allowed"
            return PluginResult(PluginResultStatus.Failed, [PluginResultPayload(stdout=stdout, stderr=None, diff=None)])

        return PluginResult(PluginResultStatus.Ok, None)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult):
        if not context.log:
            return

        log_func = context.log.info if result.status == PluginResultStatus.Ok else context.log.error
        log_func(f"Check '{cls.__name__}' finished with status: '{result.status}'")

        if result.status == PluginResultStatus.Ok:
            return

        # There is only 1 element if error happened, so we can just check the first one.
        if result.payloads and result.payloads[0].stdout:
            context.log.error(result.payloads[0].stdout)
