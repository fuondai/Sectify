# -*- coding: utf-8 -*-
import pytest
import os
import filecmp
import wave # Import wave library for frame comparison
from src.core.encryption.aes_gcm import encrypt_audio, decrypt_audio, generate_key_nonce
from src.core.storage import save_encryption_metadata, load_encryption_metadata, get_secure_path

# --- Test AES-GCM Encryption/Decryption Core Logic --- 

@pytest.fixture(scope="module")
def audio_files(tmp_path_factory):
    """Fixture để tạo tệp âm thanh mẫu và đường dẫn."""
    # Sử dụng tmp_path_factory để tạo thư mục tạm thời cho module test
    base_dir = tmp_path_factory.mktemp("aes_audio_data")
    # Đường dẫn tệp gốc (lấy từ fixtures của test)
    original_wav_path = "/home/ubuntu/crypto_project_refactored/tests/fixtures/sample.wav"
    # Đường dẫn tệp mã hóa và giải mã trong thư mục tạm thời
    encrypted_path = base_dir / "sample_encrypted_aes.bin"
    decrypted_path = base_dir / "sample_decrypted_aes.wav"
    metadata_path = base_dir / "sample_aes_metadata.json"
    
    # Kiểm tra xem tệp gốc có tồn tại không
    if not os.path.exists(original_wav_path):
        pytest.fail(f"Tệp âm thanh mẫu không tồn tại: {original_wav_path}")
        
    return {
        "original": original_wav_path,
        "encrypted": str(encrypted_path),
        "decrypted": str(decrypted_path),
        "metadata": str(metadata_path)
    }

def test_aes_gcm_encrypt_decrypt_cycle(audio_files):
    """Kiểm tra chu trình mã hóa và giải mã AES-GCM hoàn chỉnh."""
    # --- Mã hóa --- 
    encrypt_result = encrypt_audio(audio_files["original"], audio_files["encrypted"])
    assert encrypt_result is not None
    key, nonce, channels, framerate, sampwidth = encrypt_result
    
    assert os.path.exists(audio_files["encrypted"]) # Kiểm tra tệp mã hóa đã được tạo
    assert os.path.getsize(audio_files["encrypted"]) > 0 # Kiểm tra tệp mã hóa không rỗng
    
    # Lưu metadata (key, nonce, etc.) - Giả định hàm này hoạt động đúng
    metadata = {
        "key_hex": key.hex(),
        "nonce_hex": nonce.hex(),
        "channels": channels,
        "framerate": framerate,
        "sampwidth": sampwidth,
        "algorithm": "aes_gcm"
    }
    # Lưu metadata vào tệp riêng biệt cho test này
    import json
    with open(audio_files["metadata"], "w") as f:
        json.dump(metadata, f)
        
    # --- Giải mã --- 
    # Đọc lại metadata từ tệp
    with open(audio_files["metadata"], "r") as f:
        loaded_metadata = json.load(f)
        
    read_key = bytes.fromhex(loaded_metadata["key_hex"])
    read_nonce = bytes.fromhex(loaded_metadata["nonce_hex"])
    read_channels = loaded_metadata["channels"]
    read_framerate = loaded_metadata["framerate"]
    read_sampwidth = loaded_metadata["sampwidth"]
    
    decrypt_success = decrypt_audio(
        audio_files["encrypted"],
        audio_files["decrypted"],
        read_key,
        read_nonce,
        read_channels,
        read_framerate,
        read_sampwidth
    )
    assert decrypt_success == True
    assert os.path.exists(audio_files["decrypted"]) # Kiểm tra tệp giải mã đã được tạo
    
    # --- So sánh tệp gốc và tệp giải mã --- 
    # Thay vì filecmp, so sánh trực tiếp audio frames
    with wave.open(audio_files["original"], "rb") as original_wf:
        original_frames = original_wf.readframes(original_wf.getnframes())
        original_params = original_wf.getparams()
        
    with wave.open(audio_files["decrypted"], "rb") as decrypted_wf:
        decrypted_frames = decrypted_wf.readframes(decrypted_wf.getnframes())
        decrypted_params = decrypted_wf.getparams()
        
    # So sánh các tham số quan trọng (ngoại trừ nframes có thể khác nhẹ do padding/alignment)
    assert original_params[:3] == decrypted_params[:3] # channels, sampwidth, framerate
    # So sánh dữ liệu audio frames
    assert original_frames == decrypted_frames

def test_aes_gcm_decrypt_wrong_key(audio_files):
    """Kiểm tra giải mã AES-GCM với key sai."""
    encrypt_result = encrypt_audio(audio_files["original"], audio_files["encrypted"])
    assert encrypt_result is not None
    key, nonce, channels, framerate, sampwidth = encrypt_result
    
    # Tạo key sai
    wrong_key, _ = generate_key_nonce()
    assert key != wrong_key
    
    decrypt_success = decrypt_audio(
        audio_files["encrypted"],
        audio_files["decrypted"],
        wrong_key, # Sử dụng key sai
        nonce,
        channels,
        framerate,
        sampwidth
    )
    assert decrypt_success == False # Giải mã phải thất bại
    assert not os.path.exists(audio_files["decrypted"]) # Tệp giải mã không nên được tạo khi lỗi

def test_aes_gcm_decrypt_wrong_nonce(audio_files):
    """Kiểm tra giải mã AES-GCM với nonce sai."""
    encrypt_result = encrypt_audio(audio_files["original"], audio_files["encrypted"])
    assert encrypt_result is not None
    key, nonce, channels, framerate, sampwidth = encrypt_result
    
    # Tạo nonce sai
    _, wrong_nonce = generate_key_nonce()
    assert nonce != wrong_nonce
    
    decrypt_success = decrypt_audio(
        audio_files["encrypted"],
        audio_files["decrypted"],
        key,
        wrong_nonce, # Sử dụng nonce sai
        channels,
        framerate,
        sampwidth
    )
    assert decrypt_success == False # Giải mã phải thất bại
    assert not os.path.exists(audio_files["decrypted"]) 

def test_aes_gcm_decrypt_tampered_data(audio_files):
    """Kiểm tra giải mã AES-GCM với dữ liệu đã bị thay đổi."""
    encrypt_result = encrypt_audio(audio_files["original"], audio_files["encrypted"])
    assert encrypt_result is not None
    key, nonce, channels, framerate, sampwidth = encrypt_result
    
    # Thay đổi một byte trong dữ liệu mã hóa
    with open(audio_files["encrypted"], "r+b") as f:
        f.seek(10) # Đi đến byte thứ 10
        original_byte = f.read(1)
        new_byte = bytes([original_byte[0] ^ 0xFF]) # XOR với FF để thay đổi
        f.seek(10)
        f.write(new_byte)
        
    decrypt_success = decrypt_audio(
        audio_files["encrypted"],
        audio_files["decrypted"],
        key,
        nonce,
        channels,
        framerate,
        sampwidth
    )
    # AES-GCM sẽ phát hiện dữ liệu bị thay đổi qua tag xác thực
    assert decrypt_success == False 
    assert not os.path.exists(audio_files["decrypted"])

# Thêm các test case khác:
# - Test với tệp không tồn tại
# - Test với tệp không phải WAV
# - Test với metadata không chính xác (channels, framerate... sai)

