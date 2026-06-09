import logging
import sys
import time
from contextvars import ContextVar
from typing import Any

# Context variable to hold the request ID for the current task/request thread
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """
    Python logging filter to dynamically inject the request_id context variable
    into log records.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging() -> None:
    """
    Configure structured/context-aware logging.
    Logs will output in a consistent format:
    TIMESTAMP | LEVEL | [REQUEST_ID] | LOGGER_NAME | MESSAGE
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Custom filter to inject request ID
    req_id_filter = RequestIdFilter()
    handler.addFilter(req_id_filter)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | [%(request_id)s] | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    
    # Get the root logger
    root_logger = logging.getLogger()
    # Remove any default handlers to avoid duplicates
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
        
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Suppress verbose third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger with request ID injection filter.
    """
    logger = logging.getLogger(name)
    logger.addFilter(RequestIdFilter())
    return logger
