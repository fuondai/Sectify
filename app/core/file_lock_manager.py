"""
File Lock Manager to fix race conditions in audio processing
"""
import asyncio
import logging
import time
import hashlib
from typing import Dict, Set, Optional, Any
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from app.core.config import SECRET_KEY

logger = logging.getLogger(__name__)

# Track processing locks (production should use Redis)
_processing_locks: Dict[str, Dict[str, Any]] = {}
_file_locks: Dict[str, asyncio.Lock] = {}
_user_processing: Dict[str, Set[str]] = {}  # user_id -> set of track_ids being processed

class FileLockManager:
    """Manage file processing locks to prevent race conditions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.max_concurrent_per_user = 3
        self.lock_timeout_minutes = 30
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    @asynccontextmanager
    async def acquire_processing_lock(
        self, 
        track_id: str, 
        user_id: str, 
        operation: str = "processing",
        max_wait_seconds: int = 60
    ):
        """
        Acquire processing lock to prevent race conditions
        
        Args:
            track_id: Track ID being processed
            user_id: User ID performing the operation
            operation: Type of operation (processing, encryption, hls_generation)
            max_wait_seconds: Maximum time to wait for lock
            
        Raises:
            HTTPException: If lock cannot be acquired
        """
        lock_key = f"{track_id}:{operation}"
        
        # Cleanup expired locks
        self._cleanup_expired_locks()
        
        # Check user concurrent processing limit
        if self._get_user_processing_count(user_id) >= self.max_concurrent_per_user:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many concurrent processing operations. Limit: {self.max_concurrent_per_user}"
            )
        
        # Check if already being processed
        if lock_key in _processing_locks:
            existing_lock = _processing_locks[lock_key]
            if existing_lock["user_id"] == user_id:
                # Same user trying to process again
                self.logger.warning(f"User {user_id} attempting duplicate processing of track {track_id}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Track is already being processed by you"
                )
            else:
                # Different user or orphaned lock
                if self._is_lock_expired(existing_lock):
                    self.logger.info(f"Removing expired lock for track {track_id}")
                    self._release_processing_lock(lock_key)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Track is currently being processed by another operation"
                    )
        
        # Acquire file-level lock
        if track_id not in _file_locks:
            _file_locks[track_id] = asyncio.Lock()
        
        file_lock = _file_locks[track_id]
        
        try:
            # Wait for file lock với timeout
            await asyncio.wait_for(file_lock.acquire(), timeout=max_wait_seconds)
            
            # Create processing lock
            lock_data = {
                "track_id": track_id,
                "user_id": user_id,
                "operation": operation,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=self.lock_timeout_minutes),
                "process_id": self._generate_process_id(track_id, user_id, operation)
            }
            
            _processing_locks[lock_key] = lock_data
            
            # Track user processing
            if user_id not in _user_processing:
                _user_processing[user_id] = set()
            _user_processing[user_id].add(track_id)
            
            self.logger.info(f"Acquired processing lock: {lock_key} for user {user_id}")
            
            try:
                yield lock_data
            finally:
                # Release processing lock
                self._release_processing_lock(lock_key)
                
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout acquiring file lock for track {track_id}")
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Processing timeout - please try again later"
            )
        finally:
            # Always release file lock
            if file_lock.locked():
                file_lock.release()
    
    def _generate_process_id(self, track_id: str, user_id: str, operation: str) -> str:
        """Generate unique process ID"""
        data = f"{track_id}:{user_id}:{operation}:{time.time()}:{SECRET_KEY}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _is_lock_expired(self, lock_data: Dict[str, Any]) -> bool:
        """Check if lock is expired"""
        return datetime.now(timezone.utc) > lock_data["expires_at"]
    
    def _release_processing_lock(self, lock_key: str):
        """Release processing lock"""
        if lock_key in _processing_locks:
            lock_data = _processing_locks[lock_key]
            user_id = lock_data["user_id"]
            track_id = lock_data["track_id"]
            
            # Remove from processing locks
            del _processing_locks[lock_key]
            
            # Remove from user processing tracking
            if user_id in _user_processing:
                _user_processing[user_id].discard(track_id)
                if not _user_processing[user_id]:
                    del _user_processing[user_id]
            
            self.logger.info(f"Released processing lock: {lock_key}")
    
    def _get_user_processing_count(self, user_id: str) -> int:
        """Get number of tracks being processed by user"""
        return len(_user_processing.get(user_id, set()))
    
    def _cleanup_expired_locks(self):
        """Clean up expired locks"""
        if time.time() - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_locks = []
        for lock_key, lock_data in _processing_locks.items():
            if self._is_lock_expired(lock_data):
                expired_locks.append(lock_key)
        
        for lock_key in expired_locks:
            self.logger.warning(f"Cleaning up expired lock: {lock_key}")
            self._release_processing_lock(lock_key)
        
        if expired_locks:
            self.logger.info(f"Cleaned up {len(expired_locks)} expired processing locks")
        
        self.last_cleanup = time.time()
    
    def get_processing_status(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get processing status for track"""
        for lock_key, lock_data in _processing_locks.items():
            if lock_data["track_id"] == track_id:
                return {
                    "is_processing": True,
                    "operation": lock_data["operation"],
                    "started_at": lock_data["created_at"],
                    "expires_at": lock_data["expires_at"]
                }
        return None
    
    def get_user_processing_tracks(self, user_id: str) -> Set[str]:
        """Get tracks being processed by user"""
        return _user_processing.get(user_id, set()).copy()
    
    def force_release_user_locks(self, user_id: str):
        """Force release all locks for user (admin function)"""
        released_count = 0
        for lock_key, lock_data in list(_processing_locks.items()):
            if lock_data["user_id"] == user_id:
                self._release_processing_lock(lock_key)
                released_count += 1
        
        self.logger.info(f"Force released {released_count} locks for user {user_id}")
    
    async def wait_for_processing_completion(
        self, 
        track_id: str, 
        max_wait_seconds: int = 300
    ) -> bool:
        """
        Wait for track processing to complete
        
        Returns:
            True if processing completed, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            status = self.get_processing_status(track_id)
            if not status:
                return True  # No longer processing
            
            await asyncio.sleep(1)  # Wait 1 second before checking again
        
        return False  # Timeout

# Global instance
file_lock_manager = FileLockManager() 