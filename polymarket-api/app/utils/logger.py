# Logging Setup
"""
Logging configuration
"""
import json
import logging
import sys
from datetime import datetime
from pythonjsonlogger import jsonlogger
from app.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging"""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name


def setup_logging():
    """Setup application logging"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Clear existing handlers
    root = logging.getLogger()
    root.handlers.clear()
    
    # Set level
    root.setLevel(log_level)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Format based on config
    if settings.LOG_FORMAT == "json":
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
        handler.setFormatter(formatter)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    
    root.addHandler(handler)


def get_logger(name: str):
    """Get a logger instance"""
    return logging.getLogger(name)
