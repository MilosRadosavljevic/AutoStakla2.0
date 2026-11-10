"""Log grešaka u logs\\app.log + hvatanje svih neuhvaćenih izuzetaka."""
from __future__ import annotations

import logging
import platform
import sys
import threading
from logging.handlers import RotatingFileHandler
from typing import Callable

from autostakla import version
from autostakla.core import paths

log = logging.getLogger("autostakla")

# UI postavlja ovu funkciju da korisniku prikaže poruku (bez detalja).
_error_notifier: Callable[[str], None] | None = None


def setup_logging() -> None:
    paths.logs_dir().mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        paths.logs_dir() / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Ponovni poziv (npr. u testovima) ne sme da duplira handler-e.
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    root.addHandler(handler)

    sys.excepthook = _excepthook
    threading.excepthook = lambda args: _excepthook(
        args.exc_type, args.exc_value, args.exc_traceback
    )
    log.info(
        "Start %s %s (%s) | Python %s | %s",
        version.APP_NAME, version.VERSION, version.EDITION,
        platform.python_version(), platform.platform(),
    )


def set_error_notifier(fn: Callable[[str], None] | None) -> None:
    global _error_notifier
    _error_notifier = fn


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.critical("Neuhvaćena greška", exc_info=(exc_type, exc_value, exc_tb))
    if _error_notifier:
        try:
            _error_notifier(str(exc_value) or exc_type.__name__)
        except Exception:  # poruka ne sme da sruši program
            log.exception("Greška pri prikazu poruke o grešci")
