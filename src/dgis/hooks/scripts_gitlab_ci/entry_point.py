"""
This is entry point for gitlab ci.
Run this script or `dgis-gitlab-ci-run --help` to get more info.
"""

from __future__ import annotations

import argparse
import os
import sys

from dgis.hooks.plugins.discover import discover_and_load_plugins
from dgis.hooks.plugins.plugin import PluginContext, PluginResultStatus, execute_plugin
from dgis.hooks.utility.common import ExitStatus, get_version, timed_block
from dgis.hooks.utility.git import GitRef
from dgis.hooks.utility.log import init_log, log_info, log_warning, log_error, LogLevel, log_level_from_string

from git import Repo, InvalidGitRepositoryError, NoSuchPathError


def _main() -> ExitStatus:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "plugins",
        nargs="*",
        default=[],
        help="Optional list of enabled plugins. If empty then enables all packaged plugins.",
    )
    parser.add_argument(
        "--ignore-plugins", "-i",
        nargs="*",
        default=["BlackFormatCheckPlugin"],
        help="Optional list of plugin names to ignore.",
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

    log_info(f"Running CI checks version: {get_version()}")

    enabled_plugins = args.plugins if args.plugins else []
    with timed_block("Discovering plugins"):
        plugins = discover_and_load_plugins(enabled_plugins)
        ignore_plugins = args.ignore_plugins if args.ignore_plugins else []
        if ignore_plugins:
            plugins = [p for p in plugins if p.__name__ not in ignore_plugins]

    if not plugins:
        log_warning("No plugins found, nothing to check")
        return ExitStatus.Success

    with timed_block("Obtaining git repository"):
        repo_path = os.getenv("CI_PROJECT_DIR") or os.getcwd()
        try:
            git_repo = Repo(repo_path)
            log_info(f"Git repo found in '{repo_path}'")
        except (InvalidGitRepositoryError, NoSuchPathError):
            log_error(f"Invalid repository in {repo_path}")
            return ExitStatus.Error

    with timed_block("Processing checks"):
        ref = GitRef(old_rev=os.getenv("CI_COMMIT_BEFORE_SHA"), new_rev=os.getenv("CI_COMMIT_SHA"),
                     ref=os.getenv("CI_COMMIT_REF_NAME"))
        log_info(f"Using refs from CI env: {str(ref)}")
        context = PluginContext(ref, git_repo, log)
        for plugin in plugins:
            with execute_plugin(plugin, context) as result:
                if result.status == PluginResultStatus.Failed:
                    return ExitStatus.Error

    return ExitStatus.Success


def entry_point():
    sys.exit(int(_main()))


if __name__ == "__main__":
    entry_point()
