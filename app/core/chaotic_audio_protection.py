# -*- coding: utf-8 -*-
"""
Chaotic Audio Protection Module

Encrypts/decrypts WAV/MP3 audio files using the Chaotic Stream Cipher with SHA integrity checking.
This serves as an additional protection layer before files are processed into HLS.
"""

import os
import hashlib
import logging
import tempfile
import time
from typing import Tuple, Optional, Dict, Any, Callable
from pathlib import Path

from app.core.chaotic_cipher import encrypt_with_validation, decrypt_with_validation

logger = logging.getLogger(__name__)

# Supported audio formats for chaotic encryption
SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a', '.flac'}
ENCRYPTED_SUFFIX = '.encrypted'

# Progress tracking storage (in production, use Redis or database)
_progress_storage = {}

def estimate_encryption_time(file_size: int, performance_mode: str) -> float:
    """
    Estimates the encryption time based on file size and performance mode.
    
    Args:
        file_size: File size in bytes
        performance_mode: fast, balanced, secure
        
    Returns:
        Estimated time in seconds
    """
    # Base time per MB for different modes (updated ultra fast)
    time_per_mb = {
        'fast': 0.5,      # ~0.5 seconds per MB (ultra fast!)
        'balanced': 6.0,  # ~6 seconds per MB  
        'secure': 15.0    # ~15 seconds per MB
    }
    
    file_size_mb = file_size / (1024 * 1024)
    base_time = file_size_mb * time_per_mb.get(performance_mode, 6.0)
    
    # Add overhead for PBKDF2 and file I/O
    overhead = 2.0 + (file_size_mb * 0.5)
    
    return base_time + overhead

def update_progress(track_id: str, progress: float, step: str, performance_mode: str, 
                   estimated_remaining: Optional[float] = None):
    """Update progress for a track."""
    _progress_storage[track_id] = {
        'track_id': track_id,
        'status': 'processing' if progress < 100 else 'completed',
        'progress_percent': progress,
        'current_step': step,
        'estimated_remaining': estimated_remaining,
        'performance_mode': performance_mode,
        'updated_at': time.time()
    }

def get_progress(track_id: str) -> Optional[Dict]:
    """Get the progress of a track."""
    return _progress_storage.get(track_id)

class ChaoticAudioProtection:
    """
    Class wrapper for chaotic audio protection functions with progress tracking.
    """
    
    def __init__(self, master_secret: Optional[str] = None):
        """
        Initialize ChaoticAudioProtection.
        
        Args:
            master_secret: Master secret key (optional)
        """
        self.master_secret = master_secret or os.environ.get('SECTIFY_MASTER_SECRET', 'default_secret_key')
        
    def encrypt_audio_file(
        self,
        input_path: str,
        output_path: str,
        user_id: str,
        track_id: str,
        performance_mode: str = "balanced",
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Encrypts an audio file with a user-specific key and progress tracking.
        
        Args:
            input_path: Path to the original audio file
            output_path: Path for the output file
            user_id: ID of the user
            track_id: ID of the track
            performance_mode: fast, balanced, secure
            progress_callback: Optional callback function for progress updates
            
        Returns:
            A dict with success status and metadata
        """
        start_time = time.time()
        
        try:
            # Validate performance mode
            if performance_mode not in ['fast', 'balanced', 'secure']:
                performance_mode = 'balanced'
            
            # Set environment variable cho chaotic cipher
            os.environ['CHAOTIC_PERFORMANCE_MODE'] = performance_mode
            
            # Get file size và estimate time
            file_size = os.path.getsize(input_path)
            estimated_time = estimate_encryption_time(file_size, performance_mode)
            
            # Initialize progress
            update_progress(track_id, 0, "Initializing encryption...", performance_mode, estimated_time)
            if progress_callback:
                progress_callback(0, "Initializing encryption...")
            
            # Step 1: Calculate SHA-256 (10% progress)
            update_progress(track_id, 10, "Calculating file hash...", performance_mode)
            if progress_callback:
                progress_callback(10, "Calculating file hash...")
                
            original_sha256 = calculate_file_sha256(input_path)
            
            # Step 2: Generate encryption key (20% progress)
            update_progress(track_id, 20, "Generating encryption key...", performance_mode)
            if progress_callback:
                progress_callback(20, "Generating encryption key...")
                
            secret_key = create_audio_protection_key(user_id, track_id, self.master_secret)
            
            # Step 3: Read file (30% progress)
            update_progress(track_id, 30, "Reading audio file...", performance_mode)
            if progress_callback:
                progress_callback(30, "Reading audio file...")
                
            with open(input_path, 'rb') as f:
                audio_data = f.read()
            
            # Step 4: Encrypt data (30% -> 90% progress)
            update_progress(track_id, 40, f"Encrypting with {performance_mode} mode...", performance_mode)
            if progress_callback:
                progress_callback(40, f"Encrypting with {performance_mode} mode...")
            
            # Simulate progress during encryption (since we can't track internal progress)
            def encryption_progress_simulator():
                for i in range(40, 90, 10):
                    time.sleep(0.1)  # Small delay
                    remaining_time = max(0, estimated_time - (time.time() - start_time))
                    update_progress(track_id, i, f"Encrypting... ({i}%)", performance_mode, remaining_time)
                    if progress_callback:
                        progress_callback(i, f"Encrypting... ({i}%)")
            
            # Start progress simulation in background (simplified)
            encrypted_data = encrypt_with_validation(audio_data, secret_key)
            
            # Step 5: Write encrypted file (95% progress)
            update_progress(track_id, 95, "Writing encrypted file...", performance_mode)
            if progress_callback:
                progress_callback(95, "Writing encrypted file...")
                
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Step 6: Complete (100% progress)
            encryption_time = time.time() - start_time
            update_progress(track_id, 100, "Encryption completed!", performance_mode, 0)
            if progress_callback:
                progress_callback(100, "Encryption completed!")
            
            return {
                "success": True,
                "encrypted_path": output_path,
                "original_file_sha256": original_sha256,
                "user_id": user_id,
                "track_id": track_id,
                "performance_mode": performance_mode,
                "encryption_time": encryption_time,
                "estimated_time": estimated_time
            }
            
        except Exception as e:
            logger.error(f"ChaoticAudioProtection encrypt failed: {e}")
            update_progress(track_id, 0, f"Encryption failed: {str(e)}", performance_mode)
            _progress_storage[track_id]['status'] = 'failed'
            
            return {
                "success": False,
                "error": str(e),
                "performance_mode": performance_mode
            }
        finally:
            # Clean up environment variable
            if 'CHAOTIC_PERFORMANCE_MODE' in os.environ:
                del os.environ['CHAOTIC_PERFORMANCE_MODE']
    
    def decrypt_audio_file(
        self,
        encrypted_path: str,
        output_path: str,
        user_id: str,
        track_id: str,
        expected_sha256: Optional[str] = None,
        performance_mode: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Decrypts an audio file with a user-specific key.
        """
        try:
            # Set performance mode
            os.environ['CHAOTIC_PERFORMANCE_MODE'] = performance_mode
            
            # Create a user- and track-specific key
            secret_key = create_audio_protection_key(user_id, track_id, self.master_secret)
            
            # If expected_sha256 is not provided, skip the integrity check
            if expected_sha256:
                decrypted_path = decrypt_audio_file(
                    encrypted_path=encrypted_path,
                    secret_key=secret_key,
                    expected_sha256=expected_sha256,
                    output_path=output_path,
                    verify_integrity=True
                )
            else:
                # Decrypt without integrity check
                with open(encrypted_path, 'rb') as f:
                    encrypted_data = f.read()
                
                decrypted_data = decrypt_with_validation(encrypted_data, secret_key)
                
                with open(output_path, 'wb') as f:
                    f.write(decrypted_data)
                
                decrypted_path = output_path
            
            return {
                "success": True,
                "decrypted_path": decrypted_path,
                "user_id": user_id,
                "track_id": track_id,
                "performance_mode": performance_mode
            }
            
        except Exception as e:
            logger.error(f"ChaoticAudioProtection decrypt failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "performance_mode": performance_mode
            }
        finally:
            # Clean up environment variable
            if 'CHAOTIC_PERFORMANCE_MODE' in os.environ:
                del os.environ['CHAOTIC_PERFORMANCE_MODE']

def calculate_file_sha256(file_path: str) -> str:
    """
    Calculates the SHA-256 hash of a file to verify its integrity.

    Args:
        file_path: Path to the file.

    Returns:
        The hex digest of the SHA-256 hash.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read the file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating SHA-256 for {file_path}: {e}")
        raise

def encrypt_audio_file(
    input_path: str,
    secret_key: str,
    *,
    output_path: Optional[str] = None,
    preserve_extension: bool = True
) -> Tuple[str, str]:
    """
    Encrypts an audio file using the Chaotic Stream Cipher.

    Args:
        input_path: Path to the original audio file.
        secret_key: Secret key for encryption.
        output_path: Output path (optional).
        preserve_extension: Whether to preserve the original extension.

    Returns:
        A tuple containing (encrypted_file_path, original_sha256).

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the format is not supported.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Audio file not found: {input_path}")
    
    # Check format
    file_ext = Path(input_path).suffix.lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format: {file_ext}. Supported: {SUPPORTED_FORMATS}")
    
    logger.info(f"Starting chaotic encryption for: {input_path}")
    
    # Calculate SHA-256 of the original file
    original_sha256 = calculate_file_sha256(input_path)
    logger.debug(f"Original file SHA-256: {original_sha256}")
    
    # Determine output path
    if output_path is None:
        if preserve_extension:
            output_path = input_path + ENCRYPTED_SUFFIX
        else:
            output_path = Path(input_path).with_suffix(ENCRYPTED_SUFFIX).as_posix()
    
    try:
        # Read the original audio file
        with open(input_path, 'rb') as f:
            audio_data = f.read()
        
        logger.debug(f"Read {len(audio_data)} bytes from {input_path}")
        
        # Encrypt with chaotic cipher with validation
        encrypted_data = encrypt_with_validation(audio_data, secret_key)
        
        logger.debug(f"Encrypted to {len(encrypted_data)} bytes")
        
        # Save the encrypted file
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        logger.info(f"Successfully encrypted audio file: {output_path}")
        
        return output_path, original_sha256
        
    except Exception as e:
        logger.error(f"Failed to encrypt audio file {input_path}: {e}")
        # Cleanup if there is an error
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise

def decrypt_audio_file(
    encrypted_path: str,
    secret_key: str,
    expected_sha256: str,
    *,
    output_path: Optional[str] = None,
    verify_integrity: bool = True
) -> str:
    """
    Decrypts an audio file encrypted with the Chaotic Stream Cipher.

    Args:
        encrypted_path: Path to the encrypted file.
        secret_key: Secret key for decryption.
        expected_sha256: The expected SHA-256 hash of the original file.
        output_path: Output path (optional).
        verify_integrity: Whether to verify the integrity of the decrypted file.

    Returns:
        The path to the decrypted file.

    Raises:
        FileNotFoundError: If the encrypted file does not exist.
        ValueError: If the integrity check fails.
    """
    if not os.path.isfile(encrypted_path):
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_path}")
    
    logger.info(f"Starting chaotic decryption for: {encrypted_path}")
    
    # Determine output path
    if output_path is None:
        if encrypted_path.endswith(ENCRYPTED_SUFFIX):
            output_path = encrypted_path[:-len(ENCRYPTED_SUFFIX)]
        else:
            output_path = encrypted_path + '.decrypted'
    
    try:
        # Read the encrypted file
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        logger.debug(f"Read {len(encrypted_data)} bytes from {encrypted_path}")
        
        # Decrypt with chaotic cipher with validation
        decrypted_data = decrypt_with_validation(encrypted_data, secret_key)
        
        logger.debug(f"Decrypted to {len(decrypted_data)} bytes")
        
        # Save the decrypted file temporarily to check SHA
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(decrypted_data)
            temp_path = temp_file.name
        
        try:
            # Verify integrity with SHA-256
            if verify_integrity:
                actual_sha256 = calculate_file_sha256(temp_path)
                if actual_sha256 != expected_sha256:
                    raise ValueError(
                        f"Integrity check failed! Expected SHA-256: {expected_sha256}, "
                        f"but got: {actual_sha256}"
                    )
                logger.debug("SHA-256 integrity check passed")
            
            # Move the temporary file to the final location
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_path, output_path)
            
            logger.info(f"Successfully decrypted audio file: {output_path}")
            
            return output_path
            
        finally:
            # Clean up temp file if it still exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"Failed to decrypt audio file {encrypted_path}: {e}")
        # Cleanup if there is an error
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise

def secure_audio_workflow(
    input_path: str,
    secret_key: str,
    *,
    keep_encrypted: bool = True,
    temp_dir: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    Workflow for secure audio processing: Encrypt → Process → Decrypt (if needed).
    
    Args:
        input_path: Path to the original audio file.
        secret_key: Secret key.
        keep_encrypted: Whether to keep the encrypted file.
        temp_dir: Temporary directory (optional).
        
    Returns:
        A tuple containing (encrypted_path, decrypted_path, sha256_hash).
    """
    # Create temp directory if needed
    if temp_dir:
        os.makedirs(temp_dir, exist_ok=True)
        encrypted_path = os.path.join(temp_dir, Path(input_path).name + ENCRYPTED_SUFFIX)
    else:
        encrypted_path = None
    
    # Step 1: Encrypt the original file
    encrypted_path, original_sha256 = encrypt_audio_file(
        input_path, secret_key, output_path=encrypted_path
    )
    
    logger.info(f"Secure audio workflow - Encrypted: {encrypted_path}")
    
    # Step 2: Decrypt to verify (optional - can be skipped to optimize performance)
    decrypted_path = None
    
    # Step 3: Clean up if the encrypted file is not needed
    if not keep_encrypted:
        # Only delete after successful processing
        pass
    
    return encrypted_path, decrypted_path, original_sha256

def create_audio_protection_key(user_id: str, track_id: str, master_secret: str) -> str:
    """
    Creates an audio protection key from user_id, track_id, and master secret.
    
    Args:
        user_id: User ID.
        track_id: Track ID.
        master_secret: Master secret from environment.
        
    Returns:
        The derived protection key.
    """
    # Combine components
    combined = f"{user_id}:{track_id}:{master_secret}"
    
    # Use PBKDF2 to derive a strong key
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    import base64
    
    salt = hashlib.sha256(f"audio_protection:{track_id}".encode()).digest()
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=50000,  # Fewer than chaotic cipher to optimize performance
    )
    
    key_bytes = kdf.derive(combined.encode())
    # Encode to a user-friendly string
    return base64.b64encode(key_bytes).decode('ascii')

# Utility functions for integration
def is_audio_file_encrypted(file_path: str) -> bool:
    """Checks if a file is an encrypted audio file."""
    return file_path.endswith(ENCRYPTED_SUFFIX)

def get_original_filename(encrypted_path: str) -> str:
    """Gets the original filename from an encrypted file."""
    if encrypted_path.endswith(ENCRYPTED_SUFFIX):
        return encrypted_path[:-len(ENCRYPTED_SUFFIX)]
    return encrypted_path 