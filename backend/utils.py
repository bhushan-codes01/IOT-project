"""Small shared helpers for timestamps and bounded JSONL event logging."""
import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock


_LOGGER: logging.Logger | None = None
_LOGGER_LOCK = Lock()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_event_logger(log_dir: Path) -> logging.Logger:
    global _LOGGER
    with _LOGGER_LOCK:
        if _LOGGER is None:
            log_dir.mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger("fire_monitor.events")
            logger.setLevel(logging.INFO)
            handler = RotatingFileHandler(
                log_dir / "events.jsonl", maxBytes=1_000_000, backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
            logger.propagate = False
            _LOGGER = logger
        return _LOGGER


def log_event(log_dir: Path, event: dict) -> None:
    get_event_logger(log_dir).info(json.dumps(event, separators=(",", ":")))
