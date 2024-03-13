import sys

from typing import List, Any


def discover_and_load_plugins(enabled_plugins: List[str]) -> List[Any]:
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points
    discovered_plugins = entry_points(group=__package__)
    filtered_plugins = filter(lambda pl: pl.name in enabled_plugins, discovered_plugins) if enabled_plugins \
        else discovered_plugins
    return list(map(lambda pl: pl.load(), filtered_plugins))
