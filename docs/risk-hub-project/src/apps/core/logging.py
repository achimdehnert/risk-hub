"""
Logging Configuration
=====================

Structured JSON Logging für Production.
"""

import json
import logging
from datetime import datetime

from apps.core.request_context import get_context


class JsonFormatter(logging.Formatter):
    """
    JSON Log Formatter mit Request Context.
    
    Fügt automatisch hinzu:
    - timestamp
    - tenant_id
    - request_id
    - user_id
    """

    def format(self, record: logging.LogRecord) -> str:
        ctx = get_context()
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Request Context
        if ctx.tenant_id:
            log_data["tenant_id"] = str(ctx.tenant_id)
        if ctx.request_id:
            log_data["request_id"] = ctx.request_id
        if ctx.user_id:
            log_data["user_id"] = str(ctx.user_id)
        
        # Exception Info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Extra Fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    Logger mit Context-Awareness.
    
    Verwendung:
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"extra_data": {"key": "value"}})
    """
    return logging.getLogger(name)
