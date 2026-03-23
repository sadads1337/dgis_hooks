import logging
from typing import Optional

_log: Optional[logging.Logger] = None


def init_log(name: str) -> logging.Logger:
    global _log
    if _log:
        return _log
    _log = logging.getLogger(name)
    _log.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    ch.setFormatter(formatter)
    _log.addHandler(ch)
    return _log


def _get_logger() -> logging.Logger:
    # Return the configured logger if present, otherwise a default logger
    return _log if _log is not None else logging.getLogger(__name__)


def log_debug(message: str) -> None:
    _get_logger().debug(message)


def log_info(message: str) -> None:
    _get_logger().info(message)


def log_warning(message: str) -> None:
    _get_logger().warning(message)


def log_error(message: str) -> None:
    _get_logger().error(message)
