import os

from pathlib import Path


def setup_env() -> dict:
    """
    Sets up the environment for subprocesses to ensure that child python processes can import local packages
    when tests run without package install.
    """
    env = os.environ.copy()
    project_src = str(Path.cwd() / "src")
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = project_src + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = project_src
    return env
