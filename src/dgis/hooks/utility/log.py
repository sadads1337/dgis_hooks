import logging


_log = None


def init_log(name: str):
    global _log
    if _log:
        return
    _log = logging.getLogger(name)
    _log.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(name)s][%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    _log.addHandler(ch)
    return _log


def log_debug(message: str):
    _log.debug(message)


def log_info(message: str):
    _log.info(message)


def log_warning(message: str):
    _log.warning(message)


def log_error(message: str):
    _log.error(message)
