"""
Logging Configuration Module

This module provides a comprehensive logging setup with:
- Structured JSON logging with extensive context
- Request-scoped correlation tracking
- Sensitive data filtering
- Exception handling with full tracebacks
- Metrics integration
- Environment-aware formatting
- Background task logging support
"""

import contextlib
import inspect
import json
import logging
import logging.config
import os
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime, UTC
from functools import wraps
from logging import LogRecord
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import UUID

import prometheus_client
from pythonjsonlogger import jsonlogger
from typing_extensions import Protocol

from app.core.settings import settings  # FIX: import the settings instance, not the module

# Context variables for request-scoped data
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')
request_id: ContextVar[str] = ContextVar('request_id', default='')
user_id: ContextVar[Optional[Union[str, UUID]]] = ContextVar('user_id', default=None)

# Prometheus metrics for logging
LOG_EVENTS = prometheus_client.Counter(
    'log_events_total',
    'Total number of log events',
    ['level', 'module']
)

# Sensitive fields that should be masked in logs
SENSITIVE_FIELDS: Set[str] = {
    'password', 'token', 'secret', 'authorization', 'api_key', 'private_key',
    'credit_card', 'pan', 'aadhar', 'ssn', 'account_number'
}

class LoggerProtocol(Protocol):
    """Protocol defining the interface for loggers."""
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

class ContextualJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that adds extensive context and handles sensitive data.
    Includes correlation IDs, request context, and performance metrics.
    """

    def __init__(
        self,
        *args: Any,
        sensitive_fields: Optional[Set[str]] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.sensitive_fields = sensitive_fields or SENSITIVE_FIELDS

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """
        Add custom fields to the log record with sensitive data handling.
        """
        super().add_fields(log_record, record, message_dict)

        # Add basic context
        log_record['timestamp'] = datetime.fromtimestamp(record.created, UTC).isoformat()
        log_record['level'] = record.levelname
        log_record['environment'] = settings.app.ENVIRONMENT  # FIX: use settings.app.ENVIRONMENT
        
        # Add call context
        frame = inspect.currentframe()
        while frame:
            if frame.f_code.co_filename != __file__:
                log_record['file'] = frame.f_code.co_filename
                log_record['function'] = frame.f_code.co_name
                log_record['line'] = frame.f_lineno
                break
            frame = frame.f_back

        # Add request context
        try:
            log_record['correlation_id'] = correlation_id.get()
        except LookupError:
            pass

        try:
            log_record['request_id'] = request_id.get()
        except LookupError:
            pass

        try:
            user = user_id.get()
            if user:
                log_record['user_id'] = str(user)
        except LookupError:
            pass

        # Add performance metrics
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms

        # Add exception info with full traceback
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_record['exception'] = {
                'type': exc_type.__name__,
                'message': str(exc_value),
                'traceback': traceback.format_exception(exc_type, exc_value, exc_tb)
            }

        # Add custom tags
        if hasattr(record, 'tags') and record.tags:
            log_record['tags'] = record.tags

        # Mask sensitive data
        self._mask_sensitive_data(log_record)

    def _mask_sensitive_data(self, log_record: Dict[str, Any]) -> None:
        """
        Recursively mask sensitive data in the log record.
        """
        def mask_dict(d: Dict[str, Any]) -> None:
            for k, v in d.items():
                if isinstance(k, str) and any(field in k.lower() for field in self.sensitive_fields):
                    d[k] = '***MASKED***'
                elif isinstance(v, dict):
                    mask_dict(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            mask_dict(item)

        mask_dict(log_record)

class ContextualLogger(logging.Logger):
    """
    Custom logger that maintains context and provides structured logging.
    """

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        self.context: Dict[str, Any] = {}

    def _log_with_context(
        self,
        level: int,
        msg: str,
        args: tuple,
        exc_info: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        stacklevel: int = 1
    ) -> None:
        """
        Log with added context and metrics tracking.
        """
        # Track metrics
        LOG_EVENTS.labels(
            level=logging.getLevelName(level),
            module=self.name
        ).inc()

        # Merge context
        extra = extra or {}
        extra.update(self.context)

        # Add timing if not present
        if 'duration_ms' not in extra and 'start_time' in self.context:
            extra['duration_ms'] = (time.time() - self.context['start_time']) * 1000

        super()._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            extra=extra,
            stack_info=stack_info,
            stacklevel=stacklevel + 1
        )

    def bind(self, **kwargs: Any) -> 'ContextualLogger':
        """
        Create a new logger with additional context.
        """
        logger = ContextualLogger(self.name, self.level)
        logger.context = {**self.context, **kwargs}
        return logger

@contextlib.contextmanager
def log_duration(logger: LoggerProtocol, operation: str) -> None:
    """
    Context manager to log operation duration.
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = (time.time() - start_time) * 1000
        logger.info(
            f"{operation} completed",
            extra={'duration_ms': duration, 'operation': operation}
        )

def setup_logging() -> None:
    """
    Configure logging with custom formatter and handlers.
    Sets up different handlers based on environment.
    """
    # Register custom logger
    logging.setLoggerClass(ContextualLogger)

    # Create handlers
    handlers: Dict[str, Dict[str, Any]] = {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'json'
        }
    }

    # Add file handler for non-development environments
    if settings.app.ENVIRONMENT != "development":  # FIX: use settings.app.ENVIRONMENT
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_dir / f"{settings.app.ENVIRONMENT}.log",  # FIX: use settings.app.ENVIRONMENT
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json'
        }

    # Configure logging
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': ContextualJsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s',
                'json_ensure_ascii': False
            }
        },
        'handlers': handlers,
        'root': {
            'level': settings.logging.LEVEL,  # FIX: use settings.logging.LEVEL
            'handlers': list(handlers.keys())
        },
        'loggers': {
            'uvicorn': {'level': 'WARNING'},
            'sqlalchemy.engine': {'level': 'WARNING'},
            'celery': {'level': 'INFO'}
        }
    })

    # Log startup
    logger = get_logger(__name__)
    logger.info(
        "Logging configured",
        extra={
            'tags': ['startup', 'logging'],
            'environment': settings.app.ENVIRONMENT,  # FIX: use settings.app.ENVIRONMENT
            'log_level': settings.logging.LEVEL       # FIX: use settings.logging.LEVEL
        }
    )

def get_logger(name: str) -> ContextualLogger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: The name of the logger (typically __name__)
    
    Returns:
        A configured contextual logger instance
    """
    return logging.getLogger(name)  # type: ignore

def log_function_call(func: Callable) -> Callable:
    """
    Decorator to log function entry and exit with timing.
    """
    logger = get_logger(func.__module__)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            logger.debug(
                f"Entering {func.__name__}",
                extra={
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
            )
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            logger.debug(
                f"Exiting {func.__name__}",
                extra={
                    'function': func.__name__,
                    'duration_ms': duration,
                    'status': 'success'
                }
            )
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"Error in {func.__name__}",
                exc_info=True,
                extra={
                    'function': func.__name__,
                    'duration_ms': duration,
                    'status': 'error',
                    'error': str(e)
                }
            )
            raise

    return wrapper