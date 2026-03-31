import enum
import logging
from typing import Optional

_log: Optional[logging.Logger] = None


class LogLevel(enum.Enum):
    Debug = logging.DEBUG
    Info = logging.INFO
    Warning = logging.WARNING
    Error = logging.ERROR

def log_level_from_string(level_str: str) -> LogLevel:
    level_str = level_str.lower()
    if level_str == "debug":
        return LogLevel.Debug
    elif level_str == "info":
        return LogLevel.Info
    elif level_str == "warning":
        return LogLevel.Warning
    elif level_str == "error":
        return LogLevel.Error
    else:
        raise ValueError(f"Invalid log level: {level_str}. Valid levels are: debug, info, warning, error.")


def init_log(name: str, level: LogLevel = LogLevel.Info) -> logging.Logger:
    global _log
    if _log:
        return _log
    _log = logging.getLogger(name)
    _log.setLevel(level.value)
    ch = logging.StreamHandler()
    ch.setLevel(level.value)
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
