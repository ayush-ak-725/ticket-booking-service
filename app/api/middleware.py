import uuid
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger, add_correlation_id, log_request, log_response
from app.core.exceptions import BoxOfficeException


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Add correlation ID to logger
        logger = add_correlation_id(self.logger, correlation_id)
        
        # Log request
        start_time = time.time()
        log_request(
            logger,
            method=request.method,
            path=str(request.url.path),
            correlation_id=correlation_id,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None
        )
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            log_response(
                logger,
                status_code=response.status_code,
                correlation_id=correlation_id,
                process_time=process_time
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                error=str(e),
                process_time=process_time
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for error handling"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except BoxOfficeException as e:
            # Handle business logic errors
            self.logger.warning(
                "Business logic error",
                error_code=e.error_code,
                message=e.message,
                correlation_id=getattr(request.state, 'correlation_id', None)
            )
            return Response(
                content=f'{{"error": "{e.message}", "error_code": "{e.error_code}"}}',
                status_code=400,
                media_type="application/json"
            )
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(
                "Unexpected error",
                error=str(e),
                correlation_id=getattr(request.state, 'correlation_id', None)
            )
            return Response(
                content='{"error": "Internal server error", "error_code": "INTERNAL_ERROR"}',
                status_code=500,
                media_type="application/json"
            )


def setup_middleware(app):
    """Setup all middleware"""
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
