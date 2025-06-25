"""
Redis Storage Adapter for persistent storage in production
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Set, List
from datetime import datetime, timezone, timedelta
import redis.asyncio as redis
from app.core.config import SECRET_KEY
import os

logger = logging.getLogger(__name__)

class RedisStorageAdapter:
    """Redis adapter to replace in-memory storage for production"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
        # Key prefixes for different data types
        self.PROGRESS_PREFIX = "sectify:progress:"
        self.SESSION_PREFIX = "sectify:session:"
        self.TRACK_ACCESS_PREFIX = "sectify:track_access:"
        self.PROCESSING_LOCK_PREFIX = "sectify:processing_lock:"
        self.ALIAS_PREFIX = "sectify:alias:"
        self.REVOKED_SESSION_PREFIX = "sectify:revoked:"
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            self.logger.info("Connected to Redis successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False
            self.logger.info("Disconnected from Redis")
    
    # ============ PROGRESS STORAGE ============
    
    async def set_progress(self, track_id: str, progress_data: Dict[str, Any], ttl_seconds: int = 3600):
        """Store progress data"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.PROGRESS_PREFIX}{track_id}"
            await self.redis_client.setex(
                key, 
                ttl_seconds, 
                json.dumps(progress_data, default=str)
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set progress for {track_id}: {e}")
            return False
    
    async def get_progress(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get progress data"""
        if not self.connected:
            return None
            
        try:
            key = f"{self.PROGRESS_PREFIX}{track_id}"
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get progress for {track_id}: {e}")
            return None
    
    # ============ SESSION STORAGE ============
    
    async def set_session(self, session_id: str, session_data: Dict[str, Any], ttl_seconds: int = 3600):
        """Store session data"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.SESSION_PREFIX}{session_id}"
            await self.redis_client.setex(
                key,
                ttl_seconds,
                json.dumps(session_data, default=str)
            )
            
            # Also track user sessions
            user_id = session_data.get("user_id")
            if user_id:
                user_sessions_key = f"{self.SESSION_PREFIX}user:{user_id}"
                await self.redis_client.sadd(user_sessions_key, session_id)
                await self.redis_client.expire(user_sessions_key, ttl_seconds)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to set session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if not self.connected:
            return None
            
        try:
            key = f"{self.SESSION_PREFIX}{session_id}"
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str):
        """Delete session"""
        if not self.connected:
            return False
            
        try:
            # Get session data first to remove from user tracking
            session_data = await self.get_session(session_id)
            
            key = f"{self.SESSION_PREFIX}{session_id}"
            await self.redis_client.delete(key)
            
            # Remove from user sessions tracking
            if session_data and session_data.get("user_id"):
                user_sessions_key = f"{self.SESSION_PREFIX}user:{session_data['user_id']}"
                await self.redis_client.srem(user_sessions_key, session_id)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> Set[str]:
        """Get all sessions for user"""
        if not self.connected:
            return set()
            
        try:
            user_sessions_key = f"{self.SESSION_PREFIX}user:{user_id}"
            sessions = await self.redis_client.smembers(user_sessions_key)
            return set(sessions) if sessions else set()
        except Exception as e:
            self.logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return set()
    
    # ============ TRACK ACCESS STORAGE ============
    
    async def set_track_access(self, access_token: str, access_data: Dict[str, Any], ttl_seconds: int = 1800):
        """Store track access token"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.TRACK_ACCESS_PREFIX}{access_token}"
            await self.redis_client.setex(
                key,
                ttl_seconds,
                json.dumps(access_data, default=str)
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set track access token: {e}")
            return False
    
    async def get_track_access(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get track access data"""
        if not self.connected:
            return None
            
        try:
            key = f"{self.TRACK_ACCESS_PREFIX}{access_token}"
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get track access token: {e}")
            return None
    
    # ============ PROCESSING LOCKS ============
    
    async def acquire_processing_lock(
        self, 
        lock_key: str, 
        lock_data: Dict[str, Any], 
        ttl_seconds: int = 1800
    ) -> bool:
        """Acquire processing lock"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.PROCESSING_LOCK_PREFIX}{lock_key}"
            # Use SET with NX (only if not exists) and EX (expiration)
            result = await self.redis_client.set(
                key,
                json.dumps(lock_data, default=str),
                nx=True,  # Only set if key doesn't exist
                ex=ttl_seconds
            )
            return result is not None
        except Exception as e:
            self.logger.error(f"Failed to acquire processing lock {lock_key}: {e}")
            return False
    
    async def release_processing_lock(self, lock_key: str) -> bool:
        """Release processing lock"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.PROCESSING_LOCK_PREFIX}{lock_key}"
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to release processing lock {lock_key}: {e}")
            return False
    
    async def get_processing_lock(self, lock_key: str) -> Optional[Dict[str, Any]]:
        """Get processing lock data"""
        if not self.connected:
            return None
            
        try:
            key = f"{self.PROCESSING_LOCK_PREFIX}{lock_key}"
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get processing lock {lock_key}: {e}")
            return None
    
    # ============ KEY ALIAS STORAGE ============
    
    async def set_key_alias(self, alias: str, alias_data: Dict[str, Any], ttl_seconds: int = 60):
        """Store key alias"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.ALIAS_PREFIX}{alias}"
            await self.redis_client.setex(
                key,
                ttl_seconds,
                json.dumps(alias_data, default=str)
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set key alias {alias}: {e}")
            return False
    
    async def get_key_alias(self, alias: str) -> Optional[Dict[str, Any]]:
        """Get key alias data"""
        if not self.connected:
            return None
            
        try:
            key = f"{self.ALIAS_PREFIX}{alias}"
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get key alias {alias}: {e}")
            return None
    
    # ============ REVOKED SESSIONS ============
    
    async def revoke_session(self, session_id: str, ttl_seconds: int = 86400):
        """Mark session as revoked"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.REVOKED_SESSION_PREFIX}{session_id}"
            await self.redis_client.setex(key, ttl_seconds, "revoked")
            return True
        except Exception as e:
            self.logger.error(f"Failed to revoke session {session_id}: {e}")
            return False
    
    async def is_session_revoked(self, session_id: str) -> bool:
        """Check if session is revoked"""
        if not self.connected:
            return False
            
        try:
            key = f"{self.REVOKED_SESSION_PREFIX}{session_id}"
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            self.logger.error(f"Failed to check if session {session_id} is revoked: {e}")
            return False
    
    # ============ UTILITY METHODS ============
    
    async def cleanup_expired_keys(self, pattern: str):
        """Clean up expired keys (Redis handles this automatically)"""
        # Redis automatically handles TTL cleanup
        # This method is for compatibility with in-memory implementation
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        if not self.connected:
            return {}
            
        try:
            info = await self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_keys": await self.redis_client.dbsize(),
                "redis_version": info.get("redis_version", "unknown")
            }
        except Exception as e:
            self.logger.error(f"Failed to get Redis stats: {e}")
            return {}

# Global instance
redis_storage: Optional[RedisStorageAdapter] = None

async def init_redis_storage(redis_url: Optional[str] = None):
    """Initialize Redis storage"""
    global redis_storage
    redis_storage = RedisStorageAdapter(redis_url)
    await redis_storage.connect()

async def get_redis_storage() -> RedisStorageAdapter:
    """Get Redis storage instance"""
    if not redis_storage or not redis_storage.connected:
        logger.warning("Redis not available, using in-memory storage")
        raise Exception("Redis storage not initialized")
    return redis_storage 