from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from logging import Logger
from typing import Optional, Any, Type

from git import Repo

from dgis.hooks.utility.git import GitRef


class PluginResultStatus(Enum):
    Ok = 0
    Failed = 1


@dataclass
class PluginResult:
    status: PluginResultStatus
    data: Any


@dataclass
class PluginContext:
    ref: GitRef
    repo: Repo
    log: Optional[Logger] = None


class Plugin:
    @classmethod
    def execute(cls, context: PluginContext) -> PluginResult:
        """
        Executes plugin checks.
        :return: PluginResultStatus.Ok if check passed, PluginResultStatus.Failed otherwise.
        """
        return PluginResult(PluginResultStatus.Ok, None)

    @classmethod
    def post_execute(cls, context: PluginContext, result: PluginResult) -> None:
        """
        Callback after plugin executed.
        """
        pass


@contextmanager
def execute_plugin(plugin_type: Type[Plugin], plugin_context: PluginContext):
    result = PluginResult(PluginResultStatus.Failed, None)
    try:
        result = plugin_type.execute(plugin_context)
        yield result
    except Exception as error:
        if plugin_context.log:
            plugin_context.log.error(f"Exception while running '{plugin_type}: {error}'")
        yield result
    finally:
        plugin_type.post_execute(plugin_context, result)
