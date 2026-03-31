"""
This is entry point for pre receive hook.
Run this script or `dgis-pre-receive --help` to get more info.
"""

import argparse
import fileinput
import os

from dgis.hooks.plugins.plugin import PluginContext, PluginResultStatus, execute_plugin
from dgis.hooks.plugins.discover import discover_and_load_plugins
from dgis.hooks.utility.common import ExitStatus, get_version
from dgis.hooks.utility.git import parse_ref
from dgis.hooks.utility.log import init_log, log_error, log_info, log_warning, LogLevel, log_level_from_string
from dgis.hooks.utility.common import timed_block

from git import Repo, InvalidGitRepositoryError, NoSuchPathError


def _main() -> ExitStatus:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "plugins",
        nargs="*",
        default=[],
        help="Optional list of enabled plugins. "
        "If empty then hook enables all plugins from namespaces "
        "dgis.hooks.plugins and dgis.hooks.plugins.packaged.",
    )
    parser.add_argument(
        "--ignore-plugins", "-i",
        nargs="*",
        default=["BlackFormatCheckPlugin"],
        help="Optional list of plugin names to ignore (by plugin class/entry-point name). "
        "Temporary defaults to ['BlackFormatCheckPlugin'] since its experimental.",
    )
    parser.add_argument(
        "--log-level", "-l",
        type=str,
        default="info",
        help="Logging level. One of: debug, info, warning, error (case-insensitive)",
    )
    args = parser.parse_args()

    if args.log_level:
        log = init_log(__package__, log_level_from_string(args.log_level))
    else:
        log = init_log(__package__)

    log_info(f"Running pre-recieve hook version: {get_version()}")

    with timed_block("Discovering plugins"):
        enabled_plugins = args.plugins if args.plugins else []
        plugins = discover_and_load_plugins(enabled_plugins)
        for plugin in plugins:
            log_info(f"Found plugin: '{plugin.__name__}'")

        ignore_plugins = args.ignore_plugins if args.ignore_plugins else []
        if ignore_plugins:
            filtered = []
            for plugin in plugins:
                if plugin.__name__ in ignore_plugins:
                    log_info(f"Ignoring plugin: '{plugin.__name__}'")
                else:
                    filtered.append(plugin)
            plugins = filtered

    if not plugins:
        log_warning("No plugins found, nothing to check")
        return ExitStatus.Success

    with timed_block("Obtaining git repository"):
        repo_path = os.getcwd()
        try:
            git_repo = Repo(repo_path)
            log_info(f"Git repo found in '{repo_path}'")
        except (InvalidGitRepositoryError, NoSuchPathError):
            log_error(f"Invalid repository in f{repo_path}")
            return ExitStatus.Error

    with timed_block("Processing checks"):
        # Using "-" as a filename ignores argv[1:] and reads only from stdin.
        # Doc: https://docs.python.org/3/library/fileinput.html
        with fileinput.input("-") as file:
            for line in file:
                ref = parse_ref(line)
                log_info(str(ref))
                context = PluginContext(ref, git_repo, log)
                for plugin in plugins:
                    with execute_plugin(plugin, context) as result:
                        if result.status == PluginResultStatus.Failed:
                            return ExitStatus.Error

    return ExitStatus.Success


def entry_point():
    exit(int(_main()))


if __name__ == "__main__":
    entry_point()
