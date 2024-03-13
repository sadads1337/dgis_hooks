import pytest
import sys

from dgis.hooks.plugins.discover import discover_and_load_plugins


def test_empty_enabled_plugins():
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points
    expected_plugins = entry_points(group="dgis.hooks.plugins")
    plugins = discover_and_load_plugins([])

    assert all([plugin in expected_plugins for plugin in plugins])


def test_single_enabled_plugins():
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points
    expected_plugins = {"BranchCheckPlugin"}
    plugins = discover_and_load_plugins(["BranchCheckPlugin"])

    assert expected_plugins == set([plugin.__name__ for plugin in plugins])


def test_many_enabled_plugins():
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points
    expected_plugins = {"BranchCheckPlugin", "JsonCheckPlugin"}
    plugins = discover_and_load_plugins(["BranchCheckPlugin", "JsonCheckPlugin"])

    assert expected_plugins == set([plugin.__name__ for plugin in plugins])
