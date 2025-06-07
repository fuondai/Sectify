#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import wave
import numpy as np
from src.core.encryption.aes_gcm import encrypt_audio, decrypt_audio

def main():
    # Kiểm tra đường dẫn đầu vào từ tham số dòng lệnh
    if len(sys.argv) != 2:
        print("Sử dụng: py -3.10 test_aes.py <đường_dẫn_tới_file_wav>")
        return

    input_file = sys.argv[1]
    
    # Kiểm tra file đầu vào có tồn tại không
    if not os.path.exists(input_file):
        print(f"Lỗi: File '{input_file}' không tồn tại.")
        return
    
    # Tạo các đường dẫn đầu ra
    encrypted_file = f"{input_file}.encrypted"
    decrypted_file = f"{input_file}.decrypted.wav"
    
    print(f"Đang mã hóa file '{input_file}'...")
    # Mã hóa file âm thanh
    encryption_result = encrypt_audio(input_file, encrypted_file)
    
    if encryption_result is None:
        print("Mã hóa thất bại!")
        return
    
    key, nonce, channels, framerate, sampwidth = encryption_result
    print(f"Mã hóa thành công!")
    print(f"Key: {key.hex()}")
    print(f"Nonce: {nonce.hex()}")
    print(f"Channels: {channels}")
    print(f"Framerate: {framerate}")
    print(f"Sample Width: {sampwidth}")
    
    print(f"\nĐang giải mã file '{encrypted_file}'...")
    # Giải mã file
    decryption_result = decrypt_audio(encrypted_file, decrypted_file, key, nonce, channels, framerate, sampwidth)
    
    if decryption_result:
        print(f"Giải mã thành công! File đã được lưu tại '{decrypted_file}'")
    else:
        print("Giải mã thất bại!")

if __name__ == "__main__":
    main() 