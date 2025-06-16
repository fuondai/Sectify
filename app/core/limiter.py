# app/core/limiter.py
import logging
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

logger = logging.getLogger(__name__)

def get_rate_limit_key(request: Request) -> str:
    """
    Enhanced rate limiting key with advanced threat detection
    
    Uses a combination of:
    - Client IP address (with proxy detection)
    - User ID if authenticated (primary for authenticated users)
    - User-Agent fingerprinting
    - Request patterns
    
    Returns:
        Combined key for rate limiting
    """
    # Enhanced IP detection with proxy awareness
    ip = get_remote_address(request)
    
    # Check for proxy headers and validate
    forwarded_for = request.headers.get("x-forwarded-for")
    real_ip = request.headers.get("x-real-ip")
    
    # Use real IP if available and trusted
    if real_ip and _is_trusted_proxy(request):
        ip = real_ip
    elif forwarded_for and _is_trusted_proxy(request):
        # Get first IP in chain (original client)
        ip = forwarded_for.split(",")[0].strip()
    
    # Get user info if available
    user_id = None
    if hasattr(request.state, 'user') and request.state.user:
        user_id = request.state.user.id
    
    # Enhanced user agent analysis
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Detect suspicious patterns
    suspicion_score = _calculate_suspicion_score(request, user_agent, ip)
    
    # Create differentiated keys based on suspicion level
    if user_id:
        # Authenticated users: primarily user-based limiting
        if suspicion_score > 70:
            key = f"suspicious_user:{user_id}:{ip}"
        else:
            key = f"user:{user_id}"
    else:
        # Anonymous users: IP-based with enhanced detection
        ua_fingerprint = _generate_ua_fingerprint(user_agent)
        
        if suspicion_score > 50:
            # High suspicion: strict IP-based limiting
            key = f"suspicious_anon:{ip}"
        else:
            # Normal users: IP + UA fingerprint
            key = f"anon:{ip}:{ua_fingerprint}"
    
    return key

def _is_trusted_proxy(request: Request) -> bool:
    """
    Check if request comes from trusted proxy/CDN
    """
    # List of trusted proxy/CDN IP ranges (should be configurable)
    trusted_headers = ["cf-connecting-ip", "x-forwarded-for"]
    
    # Simple check - in production, implement proper IP range validation
    return any(header in request.headers for header in trusted_headers)

def _calculate_suspicion_score(request: Request, user_agent: str, ip: str) -> int:
    """
    Calculate suspicion score based on various factors (0-100)
    """
    score = 0
    
    # User agent analysis
    if not user_agent or len(user_agent) < 10:
        score += 30
    
    if any(bot in user_agent.lower() for bot in ["bot", "crawler", "spider", "scraper"]):
        score += 40
    
    if "python" in user_agent.lower() or "curl" in user_agent.lower():
        score += 25
    
    # Missing standard headers
    if not request.headers.get("accept"):
        score += 15
    
    if not request.headers.get("accept-language"):
        score += 10
    
    # Check for automation tools
    automation_indicators = ["postman", "insomnia", "httpie", "wget"]
    if any(tool in user_agent.lower() for tool in automation_indicators):
        score += 35
    
    # Suspicious header patterns
    if request.headers.get("x-requested-with") == "XMLHttpRequest" and not request.headers.get("referer"):
        score += 20
    
    # Rate of requests (simplified - would need Redis for proper implementation)
    # This would check request frequency from same IP
    
    return min(score, 100)

def _generate_ua_fingerprint(user_agent: str) -> str:
    """
    Generate user agent fingerprint for consistent rate limiting
    """
    import hashlib
    
    # Extract key components
    ua_lower = user_agent.lower()
    
    # Browser family detection
    if "chrome" in ua_lower:
        browser = "chrome"
    elif "firefox" in ua_lower:
        browser = "firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "safari"
    elif "edge" in ua_lower:
        browser = "edge"
    else:
        browser = "other"
    
    # OS detection
    if "windows" in ua_lower:
        os_family = "windows"
    elif "mac" in ua_lower:
        os_family = "mac"
    elif "linux" in ua_lower:
        os_family = "linux"
    elif "android" in ua_lower:
        os_family = "android"
    elif "ios" in ua_lower:
        os_family = "ios"
    else:
        os_family = "other"
    
    # Create fingerprint
    fingerprint_data = f"{browser}:{os_family}:{len(user_agent)}"
    return hashlib.md5(fingerprint_data.encode()).hexdigest()[:8]

def get_user_specific_key(request: Request) -> str:
    """
    User-specific rate limiting key for authenticated endpoints
    
    Returns:
        User-specific key if authenticated, IP-based key otherwise
    """
    try:
        # Try to get user from request state (set by authentication middleware)
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.id}"
    except Exception:
        pass
    
    # Fallback to IP-based limiting
    return get_remote_address(request)

def log_rate_limit_violation(request: Request, limit: str):
    """
    Log rate limit violations for security monitoring
    
    Args:
        request: FastAPI request object
        limit: Rate limit that was exceeded
    """
    ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent", "unknown")
    endpoint = str(request.url.path)
    
    # Check for suspicious patterns
    suspicious_indicators = []
    
    if "bot" in user_agent.lower():
        suspicious_indicators.append("bot_user_agent")
    
    if len(request.headers.get("user-agent", "")) < 10:
        suspicious_indicators.append("short_user_agent")
    
    if not request.headers.get("accept"):
        suspicious_indicators.append("missing_accept_header")
    
    if request.headers.get("x-forwarded-for"):
        suspicious_indicators.append("proxy_headers")
    
    log_level = logging.WARNING
    if suspicious_indicators:
        log_level = logging.ERROR
    
    logger.log(
        log_level,
        f"Rate limit exceeded: {limit} | IP: {ip} | Endpoint: {endpoint} | UA: {user_agent[:100]} | Suspicious: {suspicious_indicators}"
    )

# Initialize the enhanced Limiter
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],  # Default limit for all endpoints
)

# User-specific limiter for authenticated endpoints
user_limiter = Limiter(
    key_func=get_user_specific_key,
    default_limits=["200/minute"]  # Higher limit for authenticated users
)
