"""
Enhanced Session Management to fix authentication vulnerabilities
"""
import logging
import hashlib
import secrets
import time
from typing import Optional, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from app.core.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

# Production should use Redis for persistence and distributed environments
_active_sessions: Dict[str, Dict[str, Any]] = {}
_revoked_sessions: Set[str] = set()
_user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids

class SessionManager:
    """Enhanced session management with security features"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.max_sessions_per_user = 5  # Limit concurrent sessions
        self.session_timeout_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def create_session(
        self, 
        user_id: str, 
        client_ip: str,
        user_agent: str,
        device_fingerprint: Optional[str] = None
    ) -> str:
        """
        Create new secure session with enhanced tracking
        
        Returns:
            session_id
        """
        # Cleanup expired sessions first
        self._cleanup_expired_sessions()
        
        # Check user session limit
        current_sessions = self._get_user_sessions(user_id)
        if len(current_sessions) >= self.max_sessions_per_user:
            # Remove oldest session
            oldest_session = min(current_sessions, key=lambda sid: _active_sessions[sid]['created_at'])
            self.revoke_session(oldest_session, "session_limit_exceeded")
            self.logger.info(f"Revoked oldest session {oldest_session[:8]}... due to session limit for user {user_id}")
        
        # Generate secure session ID
        entropy = f"{user_id}:{client_ip}:{user_agent}:{time.time()}:{secrets.token_hex(32)}"
        session_id = hashlib.sha256(f"{entropy}{SECRET_KEY}".encode()).hexdigest()
        
        # Create session data
        now = datetime.now(timezone.utc)
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "client_ip": client_ip,
            "user_agent_hash": hashlib.sha256(user_agent.encode()).hexdigest()[:16],
            "device_fingerprint": device_fingerprint,
            "created_at": now,
            "last_accessed": now,
            "expires_at": now + timedelta(minutes=self.session_timeout_minutes),
            "access_count": 0,
            "is_active": True
        }
        
        # Store session
        _active_sessions[session_id] = session_data
        
        # Track user sessions
        if user_id not in _user_sessions:
            _user_sessions[user_id] = set()
        _user_sessions[user_id].add(session_id)
        
        self.logger.info(f"Created session {session_id[:8]}... for user {user_id} from IP {client_ip}")
        return session_id
    
    def validate_session(
        self, 
        session_id: str,
        client_ip: str,
        user_agent: str,
        require_ip_match: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Validate session with security checks
        
        Returns:
            session_data if valid, None otherwise
        """
        # Check if session exists
        if session_id not in _active_sessions:
            self.logger.warning(f"Session not found: {session_id[:8]}...")
            return None
        
        # Check if session is revoked
        if session_id in _revoked_sessions:
            self.logger.warning(f"Attempt to use revoked session: {session_id[:8]}...")
            return None
        
        session_data = _active_sessions[session_id]
        
        # Check expiration
        if datetime.now(timezone.utc) > session_data["expires_at"]:
            self.logger.warning(f"Expired session access attempt: {session_id[:8]}...")
            self.revoke_session(session_id, "expired")
            return None
        
        # Check if session is active
        if not session_data.get("is_active", True):
            self.logger.warning(f"Inactive session access attempt: {session_id[:8]}...")
            return None
        
        # IP binding validation with tolerance for mobile networks
        if require_ip_match and session_data["client_ip"] != client_ip:
            # Allow minor IP changes for mobile networks (same /24 subnet)
            session_ip_parts = session_data["client_ip"].split(".")
            current_ip_parts = client_ip.split(".")
            
            if len(session_ip_parts) == 4 and len(current_ip_parts) == 4:
                # Allow if only last octet changed (mobile network roaming)
                if session_ip_parts[:3] != current_ip_parts[:3]:
                    self.logger.warning(f"IP mismatch for session {session_id[:8]}...: expected {session_data['client_ip']}, got {client_ip}")
                    return None
            else:
                self.logger.warning(f"Invalid IP format in session validation")
                return None
        
        # User agent validation (fingerprinting)
        current_ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
        if session_data["user_agent_hash"] != current_ua_hash:
            self.logger.warning(f"User agent mismatch for session {session_id[:8]}...")
            # Don't immediately revoke - might be legitimate browser update
            # But log for monitoring
        
        # Update session activity
        session_data["last_accessed"] = datetime.now(timezone.utc)
        session_data["access_count"] += 1
        
        # Extend session if it's close to expiring
        if session_data["expires_at"] - datetime.now(timezone.utc) < timedelta(minutes=30):
            session_data["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=self.session_timeout_minutes)
            self.logger.debug(f"Extended session {session_id[:8]}... expiration")
        
        return session_data
    
    def revoke_session(self, session_id: str, reason: str = "manual"):
        """Revoke specific session"""
        if session_id in _active_sessions:
            session_data = _active_sessions[session_id]
            user_id = session_data["user_id"]
            
            # Mark as revoked
            _revoked_sessions.add(session_id)
            session_data["is_active"] = False
            session_data["revoked_at"] = datetime.now(timezone.utc)
            session_data["revoke_reason"] = reason
            
            # Remove from user sessions
            if user_id in _user_sessions:
                _user_sessions[user_id].discard(session_id)
            
            self.logger.info(f"Revoked session {session_id[:8]}... for user {user_id} (reason: {reason})")
    
    def revoke_user_sessions(self, user_id: str, except_session: Optional[str] = None):
        """Revoke all sessions for a user"""
        user_sessions = self._get_user_sessions(user_id)
        revoked_count = 0
        
        for session_id in list(user_sessions):
            if session_id != except_session:
                self.revoke_session(session_id, "user_logout_all")
                revoked_count += 1
        
        self.logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
    
    def _get_user_sessions(self, user_id: str) -> Set[str]:
        """Get active sessions for user"""
        if user_id not in _user_sessions:
            return set()
        
        # Filter out expired/revoked sessions
        active_sessions = set()
        for session_id in _user_sessions[user_id]:
            if (session_id in _active_sessions and 
                session_id not in _revoked_sessions and
                _active_sessions[session_id].get("is_active", True) and
                datetime.now(timezone.utc) <= _active_sessions[session_id]["expires_at"]):
                active_sessions.add(session_id)
        
        _user_sessions[user_id] = active_sessions
        return active_sessions
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        if time.time() - self.last_cleanup < self.cleanup_interval:
            return
        
        now = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session_data in _active_sessions.items():
            if session_data["expires_at"] < now:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.revoke_session(session_id, "expired")
        
        # Clean up old revoked sessions (keep for 24 hours for audit)
        old_revoked = []
        for session_id in _revoked_sessions:
            if session_id in _active_sessions:
                revoked_at = _active_sessions[session_id].get("revoked_at")
                if revoked_at and now - revoked_at > timedelta(hours=24):
                    old_revoked.append(session_id)
        
        for session_id in old_revoked:
            _revoked_sessions.discard(session_id)
            _active_sessions.pop(session_id, None)
        
        if expired_sessions or old_revoked:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired and {len(old_revoked)} old revoked sessions")
        
        self.last_cleanup = time.time()
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for monitoring"""
        if session_id not in _active_sessions:
            return None
        
        session_data = _active_sessions[session_id].copy()
        # Remove sensitive data
        session_data.pop("device_fingerprint", None)
        return session_data
    
    def get_user_session_count(self, user_id: str) -> int:
        """Get number of active sessions for user"""
        return len(self._get_user_sessions(user_id))

# Global instance
session_manager = SessionManager() 