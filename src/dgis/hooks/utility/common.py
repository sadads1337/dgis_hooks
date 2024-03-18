import shutil
import sys
import time

from contextlib import contextmanager
from enum import IntEnum
from pathlib import Path

from dgis.hooks.utility.log import log_info


class ExitStatus(IntEnum):
    Success = 0
    Error = -1


def get_version() -> str:
    if sys.version_info < (3, 10):
        from importlib_metadata import version
        return version("dgis_hooks")
    else:
        from importlib.metadata import version
        return version("dgis_hooks")


@contextmanager
def timed_block(block_name: str):
    start = time.time()
    log_info(f"Started timed block '{block_name}'")
    try:
        yield
    finally:
        end = time.time()
        elapsed_secs = "{:.2f}".format(end - start)
        log_info(f"{block_name} elapsed in {elapsed_secs} secs")


@contextmanager
def temp_dir(dir_name: Path):
    try:
        if dir_name.exists():
            shutil.rmtree(dir_name)
        dir_name.mkdir()
        yield
    finally:
        shutil.rmtree(dir_name)
