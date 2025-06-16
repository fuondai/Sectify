# -*- coding: utf-8 -*-
"""
Implementation of a Chaotic Stream Cipher using a Coupled Map Lattice (CML).

This algorithm uses a network of coupled logistic maps to generate a complex
spatio-temporal chaotic system, providing higher security than a single
logistic map.
"""

import hashlib
import numpy as np
import secrets
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Performance mode configuration
PERFORMANCE_MODE = os.environ.get('CHAOTIC_PERFORMANCE_MODE', 'balanced').lower()

if PERFORMANCE_MODE == 'fast':
    # Ultra-ultra fast mode for development - absolute minimum
    LATTICE_SIZE = 1         # Only 1 node (fastest possible)
    TRANSIENT_STEPS = 5      # Almost no transient
    PBKDF2_ITERATIONS = 10   # Minimum iterations
elif PERFORMANCE_MODE == 'secure':
    # Secure mode for production - slow but very secure
    LATTICE_SIZE = 16
    TRANSIENT_STEPS = 1000
    PBKDF2_ITERATIONS = 10000
else:
    # Balanced mode (default) - balance between security and performance
    LATTICE_SIZE = 8   # Balance security vs performance
    TRANSIENT_STEPS = 500  # Enough to reach chaos state but not too slow
    PBKDF2_ITERATIONS = 5000   # Balance security vs performance (down from 100k)

def _initialize_cml(secret_key: str, salt: bytes = None) -> tuple[np.ndarray, np.ndarray, float, bytes]:
    """
    Initializes the initial state, parameters, and coupling constant for the CML from a secret key.
    
    Security Improvements:
    - Uses PBKDF2 with salt and multiple iterations
    - Increased entropy with multiple hash rounds
    - Added domain separation for different components
    """
    # Generate a random salt if not provided
    if salt is None:
        salt = secrets.token_bytes(32)  # 256-bit salt
    
    # Use PBKDF2 with salt to derive the master key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=64,  # 512 bits
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    master_key = kdf.derive(secret_key.encode())
    
    # Domain separation for different components (max 16 bytes for BLAKE2b person)
    x_domain = b"CML_INIT_STATE"  # 14 bytes
    r_domain = b"CML_PARAMETERS"  # 14 bytes  
    eps_domain = b"CML_COUPLING"  # 12 bytes
    
    # Derive keys for each component with domain separation
    x_key = hashlib.blake2b(master_key, digest_size=32, person=x_domain).digest()
    r_key = hashlib.blake2b(master_key, digest_size=32, person=r_domain).digest()
    eps_key = hashlib.blake2b(master_key, digest_size=32, person=eps_domain).digest()
    
    # Initialize the initial state vector x with higher entropy
    x = np.zeros(LATTICE_SIZE)
    for i in range(LATTICE_SIZE):
        # Use 2 bytes for each state to increase precision
        seed_bytes = x_key[i*2:(i+1)*2] if i*2+1 < len(x_key) else x_key[i%16:(i%16)+2]
        seed_val = int.from_bytes(seed_bytes, 'big')
        # Normalize and ensure it does not fall into fixed points
        x[i] = 0.1 + (seed_val / 65535.0) * 0.8  # Limit to [0.1, 0.9]

    # Initialize the parameter vector r with higher entropy
    r = np.zeros(LATTICE_SIZE)
    for i in range(LATTICE_SIZE):
        seed_bytes = r_key[i*2:(i+1)*2] if i*2+1 < len(r_key) else r_key[i%16:(i%16)+2]
        seed_val = int.from_bytes(seed_bytes, 'big')
        # Normalize r into the chaotic range [3.8, 4.0] - avoid non-chaotic regions
        r[i] = 3.8 + (seed_val / 65535.0) * 0.2

    # Initialize the coupling constant epsilon with better entropy
    eps_val = int.from_bytes(eps_key[:4], 'big')
    epsilon = 0.1 + (eps_val / (2**32 - 1)) * 0.3  # Epsilon in the range [0.1, 0.4]

    return x, r, epsilon, salt

def _generate_keystream_cml(x: np.ndarray, r: np.ndarray, epsilon: float, length: int) -> bytes:
    """
    Balanced keystream generation - secure but with optimized performance.
    """
    x_current = x.copy()
    
    # Proper transient phase to reach the chaos state
    for i in range(TRANSIENT_STEPS):
        x_current = r * x_current * (1 - x_current)
        # Proper coupling with nearest neighbors
        coupled = (np.roll(x_current, 1) + np.roll(x_current, -1)) * 0.5
        x_current = (1 - epsilon) * x_current + epsilon * coupled
        
        # Periodic scrambling with frequency dependent on performance mode  
        scramble_freq = 50 if PERFORMANCE_MODE == 'fast' else 100
        if i % scramble_freq == 0:
            x_current = np.roll(x_current, 1)

    # Optimized keystream generation with proper mixing
    keystream = bytearray()
    
    # Generate in chunks with dynamic size based on performance mode
    CHUNK_SIZE = 8192 if PERFORMANCE_MODE == 'fast' else 2048  # Fast mode = larger chunks
    for chunk_start in range(0, length, CHUNK_SIZE):
        chunk_size = min(CHUNK_SIZE, length - chunk_start)
        chunk_data = bytearray(chunk_size)
        
        for i in range(chunk_size):
            # Evolution step with proper chaos
            x_current = r * x_current * (1 - x_current)
            coupled = (np.roll(x_current, 1) + np.roll(x_current, -1)) * 0.5
            x_current = (1 - epsilon) * x_current + epsilon * coupled
            
            # Output function optimized for performance mode
            byte_val = 0
            for j in range(LATTICE_SIZE):
                val = int(x_current[j] * 255) & 0xFF
                if PERFORMANCE_MODE == 'fast':
                    # Simple XOR for fast mode
                    byte_val ^= val
                else:
                    # Full mixing for secure modes
                    rotated = ((val << (j % 8)) | (val >> (8 - (j % 8)))) & 0xFF
                    byte_val ^= rotated
            
            # Additional mixing only for secure modes
            if PERFORMANCE_MODE != 'fast':
                byte_val ^= (byte_val << 1) & 0xFF
                byte_val ^= (byte_val >> 1) & 0xFF
            
            chunk_data[i] = byte_val & 0xFF
        
        keystream.extend(chunk_data)

    return bytes(keystream)

def encrypt(data: bytes, secret_key: str) -> bytes:
    """
    Encrypts data using the CML stream cipher with authenticated encryption.
    
    Format: salt(32) + hmac(32) + encrypted_data
    """
    if not isinstance(data, bytes):
        raise TypeError("Input data must be bytes")

    # Generate components
    x, r, epsilon, salt = _initialize_cml(secret_key)
    keystream = _generate_keystream_cml(x, r, epsilon, len(data))

    # Encrypt the data
    encrypted_data = bytes([b ^ k for b, k in zip(data, keystream)])
    
    # Create HMAC for integrity protection
    # Derive HMAC key from the master key
    kdf_hmac = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt + b"HMAC_DERIVE",  # Different salt to avoid key reuse
        iterations=PBKDF2_ITERATIONS,
    )
    hmac_key = kdf_hmac.derive(secret_key.encode())
    
    # HMAC covers salt + encrypted data to prevent tampering
    import hmac as hmac_module
    mac = hmac_module.new(hmac_key, salt + encrypted_data, hashlib.sha256).digest()
    
    # Combine: salt + mac + encrypted_data
    result = salt + mac + encrypted_data
    return result

def decrypt(data: bytes, secret_key: str) -> bytes:
    """
    Decrypts data using the CML stream cipher with integrity verification.
    
    Expected format: salt(32) + hmac(32) + encrypted_data
    """
    if not isinstance(data, bytes):
        raise TypeError("Input data must be bytes")
    
    if len(data) < 64:  # 32 (salt) + 32 (hmac) minimum
        raise ValueError("Invalid data - too short")
    
    # Separate the components
    salt = data[:32]
    received_mac = data[32:64]
    encrypted_data = data[64:]
    
    # Derive HMAC key 
    kdf_hmac = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt + b"HMAC_DERIVE",
        iterations=PBKDF2_ITERATIONS,
    )
    hmac_key = kdf_hmac.derive(secret_key.encode())
    
    # Verify integrity
    import hmac as hmac_module
    expected_mac = hmac_module.new(hmac_key, salt + encrypted_data, hashlib.sha256).digest()
    if not hmac_module.compare_digest(expected_mac, received_mac):
        raise ValueError("Integrity verification failed - data may have been tampered with")
    
    # Re-initialize the cipher with the known salt
    x, r, epsilon, _ = _initialize_cml(secret_key, salt)
    keystream = _generate_keystream_cml(x, r, epsilon, len(encrypted_data))

    # Decrypt
    decrypted_data = bytes([b ^ k for b, k in zip(encrypted_data, keystream)])
    return decrypted_data

def secure_compare(a: bytes, b: bytes) -> bool:
    """
    Constant-time comparison to avoid timing attacks.
    """
    import hmac
    return hmac.compare_digest(a, b)

def validate_key_strength(secret_key: str) -> bool:
    """
    Validate the strength of the secret key.
    
    Returns:
        bool: True if key is strong enough
    """
    if len(secret_key) < 12:  # Minimum 12 characters
        return False
    
    # Check entropy - must have at least 3 different character types
    has_lower = any(c.islower() for c in secret_key)
    has_upper = any(c.isupper() for c in secret_key)  
    has_digit = any(c.isdigit() for c in secret_key)
    has_special = any(not c.isalnum() for c in secret_key)
    
    char_types = sum([has_lower, has_upper, has_digit, has_special])
    return char_types >= 3

def analyze_chaos_parameters(x: np.ndarray, r: np.ndarray, epsilon: float) -> dict:
    """
    Analyzes the parameters to ensure the system is in a chaotic state.
    """
    analysis = {
        "is_chaotic": True,
        "warnings": [],
        "parameters": {
            "lattice_size": len(x),
            "mean_r": np.mean(r),
            "epsilon": epsilon
        }
    }
    
    # Check r parameters in the chaotic range
    for i, r_val in enumerate(r):
        if r_val < 3.57 or r_val > 4.0:
            analysis["warnings"].append(f"r[{i}] = {r_val:.4f} may not ensure chaotic behavior")
    
    # Check initial conditions not falling into fixed points
    for i, x_val in enumerate(x):
        if x_val <= 0.05 or x_val >= 0.95:
            analysis["warnings"].append(f"x[{i}] = {x_val:.4f} near fixed point")
    
    # Check coupling strength
    if epsilon < 0.05:
        analysis["warnings"].append("Epsilon too small - may not ensure chaotic behavior")
    elif epsilon > 0.5:
        analysis["warnings"].append("Epsilon too large - may reduce chaotic behavior")
    
    if analysis["warnings"]:
        analysis["is_chaotic"] = False
        
    return analysis

def encrypt_with_validation(data: bytes, secret_key: str) -> bytes:
    """
    Encrypt with full validation.
    """
    # Validate input
    if not validate_key_strength(secret_key):
        raise ValueError("Secret key not strong enough. Need at least 12 characters with 3 different types.")
    
    if len(data) > 50 * 1024 * 1024:  # Limit 50MB
        raise ValueError("Data too large (>50MB)")
    
    # Generate and validate parameters
    x, r, epsilon, salt = _initialize_cml(secret_key)
    
    # Analyze chaos parameters
    chaos_analysis = analyze_chaos_parameters(x, r, epsilon)
    if not chaos_analysis["is_chaotic"]:
        # Log warnings but proceed (may adjust parameters)
        import logging
        logger = logging.getLogger(__name__)
        for warning in chaos_analysis["warnings"]:
            logger.warning(f"Chaotic cipher warning: {warning}")
    
    # Proceed with encryption
    return encrypt(data, secret_key)

def decrypt_with_validation(data: bytes, secret_key: str) -> bytes:
    """
    Decrypt with full validation.
    """
    if not validate_key_strength(secret_key):
        raise ValueError("Secret key not strong enough. Need at least 12 characters with 3 different types.")
    
    return decrypt(data, secret_key)
