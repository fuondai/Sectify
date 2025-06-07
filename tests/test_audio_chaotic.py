# -*- coding: utf-8 -*-
import pytest
import os
import filecmp
import wave # Import wave library for frame comparison
from hashlib import sha256
from src.core.encryption.chaotic import encrypt_audio_chaotic, decrypt_audio_chaotic

# --- Test Chaotic Stream Encryption/Decryption Core Logic --- 

@pytest.fixture(scope="module")
def chaotic_audio_files(tmp_path_factory):
    """Fixture để tạo tệp âm thanh mẫu và đường dẫn cho test chaotic."""
    base_dir = tmp_path_factory.mktemp("chaotic_audio_data")
    original_wav_path = "/home/ubuntu/crypto_project_refactored/tests/fixtures/sample.wav"
    encrypted_path = base_dir / "sample_encrypted_chaotic.bin"
    decrypted_path = base_dir / "sample_decrypted_chaotic.wav"
    
    if not os.path.exists(original_wav_path):
        pytest.fail(f"Tệp âm thanh mẫu không tồn tại: {original_wav_path}")
        
    return {
        "original": original_wav_path,
        "encrypted": str(encrypted_path),
        "decrypted": str(decrypted_path),
        "seed": b"correct_seed_material_for_test" # Seed mẫu cho test
    }

def test_chaotic_encrypt_decrypt_cycle(chaotic_audio_files):
    """Kiểm tra chu trình mã hóa và giải mã Chaotic Stream hoàn chỉnh."""
    # --- Mã hóa --- 
    encrypt_result = encrypt_audio_chaotic(
        chaotic_audio_files["original"],
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["seed"]
    )
    assert encrypt_result is not None
    channels, framerate, sampwidth, original_hash = encrypt_result
    
    assert os.path.exists(chaotic_audio_files["encrypted"]) 
    assert os.path.getsize(chaotic_audio_files["encrypted"]) > 0
    assert len(original_hash) == 64 # SHA256 hash length
    
    # --- Giải mã --- 
    decrypt_success = decrypt_audio_chaotic(
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["decrypted"],
        chaotic_audio_files["seed"], # Sử dụng đúng seed
        channels,
        framerate,
        sampwidth,
        original_hash # Sử dụng đúng hash gốc
    )
    assert decrypt_success == True
    assert os.path.exists(chaotic_audio_files["decrypted"]) 
    
    # --- So sánh tệp gốc và tệp giải mã --- 
    # Thay vì filecmp, so sánh trực tiếp audio frames và params
    with wave.open(chaotic_audio_files["original"], "rb") as original_wf:
        original_frames = original_wf.readframes(original_wf.getnframes())
        original_params = original_wf.getparams()
        
    with wave.open(chaotic_audio_files["decrypted"], "rb") as decrypted_wf:
        decrypted_frames = decrypted_wf.readframes(decrypted_wf.getnframes())
        decrypted_params = decrypted_wf.getparams()
        
    # So sánh các tham số quan trọng
    assert original_params[:3] == decrypted_params[:3] # channels, sampwidth, framerate
    # So sánh dữ liệu audio frames
    assert original_frames == decrypted_frames

def test_chaotic_decrypt_wrong_seed(chaotic_audio_files):
    """Kiểm tra giải mã Chaotic Stream với seed sai."""
    encrypt_result = encrypt_audio_chaotic(
        chaotic_audio_files["original"],
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["seed"]
    )
    assert encrypt_result is not None
    channels, framerate, sampwidth, original_hash = encrypt_result
    
    wrong_seed = b"this_is_the_wrong_seed"
    assert chaotic_audio_files["seed"] != wrong_seed
    
    # Giải mã với seed sai sẽ tạo keystream sai -> dữ liệu giải mã sai -> hash sai
    decrypt_success = decrypt_audio_chaotic(
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["decrypted"],
        wrong_seed, # Sử dụng seed sai
        channels,
        framerate,
        sampwidth,
        original_hash
    )
    # Hàm giải mã sẽ trả về False do hash không khớp
    assert decrypt_success == False 
    assert not os.path.exists(chaotic_audio_files["decrypted"]) # Không ghi tệp khi hash sai

def test_chaotic_decrypt_wrong_hash(chaotic_audio_files):
    """Kiểm tra giải mã Chaotic Stream với hash gốc mong đợi sai."""
    encrypt_result = encrypt_audio_chaotic(
        chaotic_audio_files["original"],
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["seed"]
    )
    assert encrypt_result is not None
    channels, framerate, sampwidth, original_hash = encrypt_result
    
    wrong_hash = "a" * 64 # Hash sai
    assert original_hash != wrong_hash
    
    # Giải mã với hash mong đợi sai
    decrypt_success = decrypt_audio_chaotic(
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["decrypted"],
        chaotic_audio_files["seed"],
        channels,
        framerate,
        sampwidth,
        wrong_hash # Sử dụng hash sai
    )
    # Hàm giải mã sẽ trả về False do hash không khớp
    assert decrypt_success == False 
    assert not os.path.exists(chaotic_audio_files["decrypted"]) 

def test_chaotic_decrypt_tampered_data(chaotic_audio_files):
    """Kiểm tra giải mã Chaotic Stream với dữ liệu mã hóa bị thay đổi."""
    encrypt_result = encrypt_audio_chaotic(
        chaotic_audio_files["original"],
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["seed"]
    )
    assert encrypt_result is not None
    channels, framerate, sampwidth, original_hash = encrypt_result
    
    # Thay đổi một byte trong dữ liệu mã hóa
    with open(chaotic_audio_files["encrypted"], "r+b") as f:
        f.seek(5) 
        original_byte = f.read(1)
        new_byte = bytes([original_byte[0] ^ 0xAA]) # XOR để thay đổi
        f.seek(5)
        f.write(new_byte)
        
    # Giải mã dữ liệu đã bị thay đổi
    decrypt_success = decrypt_audio_chaotic(
        chaotic_audio_files["encrypted"],
        chaotic_audio_files["decrypted"],
        chaotic_audio_files["seed"],
        channels,
        framerate,
        sampwidth,
        original_hash
    )
    # Dữ liệu giải mã sẽ khác gốc -> hash không khớp
    assert decrypt_success == False 
    assert not os.path.exists(chaotic_audio_files["decrypted"])

# Thêm các test case khác:
# - Test với tệp không tồn tại
# - Test với tệp không phải WAV khi mã hóa
# - Test trường hợp không tạo đủ keystream (nếu có thể mô phỏng)

