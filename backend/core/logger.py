# core/logger.py
import json
import logging
import os

from contextvars import ContextVar
from logging import LogRecord
from logging.handlers import RotatingFileHandler

request_id_ctx_var = ContextVar("request_id", default=None)

LOG_DIR = "logs"   # relative to backend root
LOG_FILE = os.path.join(LOG_DIR, "app.log")
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5  # Keep 5 backups

class JsonFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        return json.dumps(log_entry)

class RequestIdFilter(logging.Filter):
    def filter(self, record: LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True

def get_logger(name: str) -> logging.Logger:
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # File Handler (JSON)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    file_handler.setFormatter(JsonFormatter())
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Add Request ID filter
    logger.addFilter(RequestIdFilter())

    return logger
