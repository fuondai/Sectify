"""
Secure Error Handler to prevent information disclosure
"""
import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.config import IS_PRODUCTION

logger = logging.getLogger(__name__)

# Generic error messages for production
GENERIC_ERROR_MESSAGES = {
    400: "Invalid request parameters",
    401: "Authentication required", 
    403: "Access denied",
    404: "Resource not found",
    405: "Method not allowed",
    409: "Resource conflict",
    413: "Request entity too large",
    415: "Unsupported media type",
    429: "Too many requests",
    500: "Internal server error",
    502: "Bad gateway",
    503: "Service unavailable"
}

class SecureErrorHandler:
    """Handle errors securely to prevent information disclosure"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_exception(
        self, 
        request: Request, 
        exc: Exception,
        include_details: bool = False
    ) -> JSONResponse:
        """
        Handle exception securely
        
        Args:
            request: FastAPI request
            exc: Exception that occurred
            include_details: Whether to include detailed error info (dev mode only)
            
        Returns:
            Secure JSON response
        """
        # Determine if we should include details
        show_details = include_details and not IS_PRODUCTION
        
        # Extract client info for logging
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        endpoint = str(request.url.path)
        
        if isinstance(exc, HTTPException):
            # Handle known HTTP exceptions
            status_code = exc.status_code
            
            # Log security-relevant errors
            if status_code in [401, 403, 404]:
                self.logger.warning(
                    f"Security event: {status_code} at {endpoint} | "
                    f"IP: {client_ip} | UA: {user_agent[:100]} | "
                    f"Detail: {exc.detail if show_details else 'hidden'}"
                )
            elif status_code >= 500:
                self.logger.error(
                    f"Server error: {status_code} at {endpoint} | "
                    f"IP: {client_ip} | Detail: {exc.detail}"
                )
            
            # Prepare response
            error_detail = exc.detail if show_details else GENERIC_ERROR_MESSAGES.get(status_code, "Error occurred")
            
            response_data = {
                "error": True,
                "status_code": status_code,
                "message": error_detail,
                "timestamp": self._get_timestamp(),
                "path": endpoint
            }
            
            # Add debug info only in development
            if show_details and not IS_PRODUCTION:
                response_data["debug"] = {
                    "exception_type": type(exc).__name__,
                    "original_detail": exc.detail
                }
            
            return JSONResponse(
                status_code=status_code,
                content=response_data
            )
        
        elif isinstance(exc, ValueError):
            # Handle validation errors
            self.logger.warning(
                f"Validation error at {endpoint} | "
                f"IP: {client_ip} | Error: {str(exc) if show_details else 'validation failed'}"
            )
            
            response_data = {
                "error": True,
                "status_code": 400,
                "message": str(exc) if show_details else "Invalid input data",
                "timestamp": self._get_timestamp(),
                "path": endpoint
            }
            
            return JSONResponse(
                status_code=400,
                content=response_data
            )
        
        else:
            # Handle unexpected exceptions
            error_id = self._generate_error_id()
            
            # Log full error details server-side
            self.logger.error(
                f"Unexpected error [{error_id}] at {endpoint} | "
                f"IP: {client_ip} | Type: {type(exc).__name__} | "
                f"Error: {str(exc)}"
            )
            
            # Log stack trace for debugging
            if not IS_PRODUCTION:
                self.logger.error(f"Stack trace [{error_id}]: {traceback.format_exc()}")
            
            # Return generic error to client
            response_data = {
                "error": True,
                "status_code": 500,
                "message": "An unexpected error occurred",
                "error_id": error_id if show_details else None,
                "timestamp": self._get_timestamp(),
                "path": endpoint
            }
            
            # Add debug info only in development
            if show_details and not IS_PRODUCTION:
                response_data["debug"] = {
                    "exception_type": type(exc).__name__,
                    "error_message": str(exc),
                    "stack_trace": traceback.format_exc().split('\n')[-10:]  # Last 10 lines
                }
            
            return JSONResponse(
                status_code=500,
                content=response_data
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP safely"""
        # Check for proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def log_security_event(
        self, 
        event_type: str, 
        request: Request, 
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security events for monitoring"""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        endpoint = str(request.url.path)
        
        # Check for suspicious patterns
        suspicion_indicators = []
        
        if len(user_agent) < 10:
            suspicion_indicators.append("short_ua")
        
        if "bot" in user_agent.lower() or "crawler" in user_agent.lower():
            suspicion_indicators.append("bot_ua")
        
        if not request.headers.get("accept"):
            suspicion_indicators.append("missing_accept")
        
        # Log with appropriate level
        log_level = logging.ERROR if suspicion_indicators else logging.WARNING
        
        log_data = {
            "event_type": event_type,
            "endpoint": endpoint,
            "client_ip": client_ip,
            "user_agent": user_agent[:100],
            "suspicion_indicators": suspicion_indicators,
            "timestamp": self._get_timestamp()
        }
        
        if details:
            log_data.update(details)
        
        self.logger.log(
            log_level,
            f"Security event: {event_type} | Data: {log_data}"
        )

# Global instance
secure_error_handler = SecureErrorHandler()

# Utility functions for common errors
def create_security_error(message: str = "Access denied") -> HTTPException:
    """Create standardized security error"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message if not IS_PRODUCTION else "Access denied"
    )

def create_validation_error(message: str = "Invalid input") -> HTTPException:
    """Create standardized validation error"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message if not IS_PRODUCTION else "Invalid request parameters"
    )

def create_not_found_error(resource: str = "Resource") -> HTTPException:
    """Create standardized not found error"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found" if not IS_PRODUCTION else "Resource not found"
    )

def create_conflict_error(message: str = "Resource conflict") -> HTTPException:
    """Create standardized conflict error"""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message if not IS_PRODUCTION else "Resource conflict"
    )

def create_rate_limit_error(message: str = "Too many requests") -> HTTPException:
    """Create standardized rate limit error"""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=message if not IS_PRODUCTION else "Too many requests"
    ) 