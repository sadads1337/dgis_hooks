import sys

from typing import List, Any

from dgis.hooks.utility.log import log_info


def discover_and_load_plugins() -> List[Any]:
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points
    discovered_plugins = entry_points(group=__package__)
    for plugin in discovered_plugins:
        log_info(f"Discovered plugin: '{plugin.name}'")
    return list(map(lambda pl: pl.load(), discovered_plugins))