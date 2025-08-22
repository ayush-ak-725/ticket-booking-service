import sys
import structlog
from typing import Any, Dict
from .config import config


def setup_logging() -> None:
    """Setup structured logging with correlation IDs"""
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if config.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger with the given name"""
    return structlog.get_logger(name)


def add_correlation_id(logger: structlog.BoundLogger, correlation_id: str) -> structlog.BoundLogger:
    """Add correlation ID to logger context"""
    return logger.bind(correlation_id=correlation_id)


def log_request(logger: structlog.BoundLogger, method: str, path: str, 
                correlation_id: str, **kwargs) -> None:
    """Log incoming request"""
    logger.info(
        "Incoming request",
        method=method,
        path=path,
        correlation_id=correlation_id,
        **kwargs
    )


def log_response(logger: structlog.BoundLogger, status_code: int, 
                correlation_id: str, **kwargs) -> None:
    """Log response"""
    logger.info(
        "Response sent",
        status_code=status_code,
        correlation_id=correlation_id,
        **kwargs
    )

