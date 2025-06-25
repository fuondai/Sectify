"""
Centralized Authorization Service to fix IDOR vulnerabilities
"""
import logging
import hashlib
import secrets
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status
from app.schemas.user import UserInDB
from app.crud.audio import get_track_by_id
from app.core.config import SECRET_KEY
from app.core.validation import validate_uuid

logger = logging.getLogger(__name__)

# Secure session storage for track access (production should use Redis)
_secure_track_sessions: Dict[str, Dict[str, Any]] = {}

class AuthorizationService:
    """Centralized authorization service to prevent IDOR attacks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def check_track_access(
        self, 
        track_id: str, 
        user: Optional[UserInDB], 
        db: AsyncIOMotorDatabase,
        operation: str = "read",  # read, write, delete, stream
        client_ip: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Centralized track access checking with enhanced security
        
        Returns:
            (track_data, secure_access_token)
            
        Raises:
            HTTPException: If access denied
        """
        # Validate track ID format
        validated_track_id = validate_uuid(track_id, "track_id")
        
        # Get track from database
        track = await get_track_by_id(db, validated_track_id)
        if not track:
            self.logger.warning(f"Track not found: {validated_track_id} by user {user.id if user else 'anonymous'}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Track not found"
            )
        
        # Check basic permissions
        is_public = track.get("is_public", False)
        owner_id = track.get("owner_id")
        
        # Permission matrix
        access_granted = False
        
        if operation == "read" or operation == "stream":
            # Public tracks: anyone can read/stream
            # Private tracks: only owner
            access_granted = is_public or (user and user.id == owner_id)
            
        elif operation == "write":
            # Only owner can modify
            access_granted = user and user.id == owner_id
            
        elif operation == "delete":
            # Only owner can delete
            access_granted = user and user.id == owner_id
            
        else:
            self.logger.warning(f"Unknown operation: {operation}")
            access_granted = False
        
        if not access_granted:
            self.logger.warning(f"Access denied: {operation} on track {validated_track_id} by user {user.id if user else 'anonymous'}")
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this track"
                )
        
        # Generate secure access token for this session
        access_token = self._create_secure_access_token(
            validated_track_id, 
            user.id if user else "anonymous",
            operation,
            client_ip
        )
        
        self.logger.info(f"Access granted: {operation} on track {validated_track_id} by user {user.id if user else 'anonymous'}")
        return track, access_token
    
    def _create_secure_access_token(
        self, 
        track_id: str, 
        user_id: str, 
        operation: str,
        client_ip: Optional[str] = None,
        ttl_minutes: int = 30
    ) -> str:
        """
        Create secure access token for track session to prevent replay attacks
        """
        # Create unique session ID
        session_data = f"{track_id}:{user_id}:{operation}:{client_ip}:{datetime.now(timezone.utc).isoformat()}"
        session_id = hashlib.sha256(f"{session_data}{SECRET_KEY}{secrets.token_hex(16)}".encode()).hexdigest()[:32]
        
        # Store session with expiration
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        _secure_track_sessions[session_id] = {
            "track_id": track_id,
            "user_id": user_id,
            "operation": operation,
            "client_ip": client_ip,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        }
        
        return session_id
    
    def validate_secure_access_token(
        self, 
        token: str, 
        track_id: str, 
        user_id: Optional[str] = None,
        operation: str = "read",
        client_ip: Optional[str] = None
    ) -> bool:
        """
        Validate secure access token to prevent unauthorized access
        """
        try:
            # Clean expired sessions
            self._cleanup_expired_sessions()
            
            session = _secure_track_sessions.get(token)
            if not session:
                self.logger.warning(f"Invalid or expired access token: {token[:8]}...")
                return False
            
            # Check expiration
            if datetime.now(timezone.utc) > session["expires_at"]:
                self.logger.warning(f"Expired access token: {token[:8]}...")
                del _secure_track_sessions[token]
                return False
            
            # Validate session parameters
            if session["track_id"] != track_id:
                self.logger.warning(f"Track ID mismatch in session: expected {track_id}, got {session['track_id']}")
                return False
            
            if user_id and session["user_id"] != user_id:
                self.logger.warning(f"User ID mismatch in session: expected {user_id}, got {session['user_id']}")
                return False
            
            if session["operation"] != operation:
                self.logger.warning(f"Operation mismatch in session: expected {operation}, got {session['operation']}")
                return False
            
            # IP binding validation (with some tolerance for mobile networks)
            if client_ip and session["client_ip"]:
                if session["client_ip"] != client_ip:
                    # Allow minor IP changes (last octet for mobile networks)
                    session_ip_parts = session["client_ip"].split(".")
                    current_ip_parts = client_ip.split(".")
                    
                    if len(session_ip_parts) == 4 and len(current_ip_parts) == 4:
                        # Check if only last octet changed (mobile network tolerance)
                        if session_ip_parts[:3] != current_ip_parts[:3]:
                            self.logger.warning(f"IP mismatch in session: expected {session['client_ip']}, got {client_ip}")
                            return False
                    else:
                        self.logger.warning(f"IP format mismatch in session")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating access token: {e}")
            return False
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token for token, session in _secure_track_sessions.items()
            if session["expires_at"] < now
        ]
        
        for token in expired_tokens:
            del _secure_track_sessions[token]
        
        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired access tokens")
    
    def revoke_user_sessions(self, user_id: str):
        """Revoke all sessions for a specific user"""
        revoked_count = 0
        for token, session in list(_secure_track_sessions.items()):
            if session["user_id"] == user_id:
                del _secure_track_sessions[token]
                revoked_count += 1
        
        self.logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
    
    def generate_secure_watermark_id(
        self, 
        track_id: str, 
        user_id: Optional[str],
        client_ip: Optional[str],
        session_token: str
    ) -> str:
        """
        Generate secure watermark ID based on session instead of predictable hash
        """
        # Combine multiple entropy sources
        entropy_data = f"{track_id}:{user_id}:{client_ip}:{session_token}:{datetime.now(timezone.utc).isoformat()}"
        random_salt = secrets.token_hex(16)
        
        # Create secure hash
        secure_hash = hashlib.sha256(f"{entropy_data}{SECRET_KEY}{random_salt}".encode()).hexdigest()[:16]
        
        return f"{track_id}_{secure_hash}"

# Global instance
authorization_service = AuthorizationService() 