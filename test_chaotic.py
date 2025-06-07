#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import wave
import numpy as np
from src.core.encryption.chaotic import encrypt_audio_chaotic, decrypt_audio_chaotic

def main():
    # Kiểm tra đường dẫn đầu vào từ tham số dòng lệnh
    if len(sys.argv) != 2:
        print("Sử dụng: py -3.10 test_chaotic.py <đường_dẫn_tới_file_wav>")
        return

    input_file = sys.argv[1]
    
    # Kiểm tra file đầu vào có tồn tại không
    if not os.path.exists(input_file):
        print(f"Lỗi: File '{input_file}' không tồn tại.")
        return
    
    # Tạo các đường dẫn đầu ra
    encrypted_file = f"{input_file}.encrypted.chaotic"
    decrypted_file = f"{input_file}.decrypted.chaotic.wav"
    
    # Tạo seed ngẫu nhiên
    seed_material = os.urandom(32)
    print(f"Seed hex: {seed_material.hex()}")
    
    print(f"Đang mã hóa file '{input_file}'...")
    # Mã hóa file âm thanh
    encryption_result = encrypt_audio_chaotic(input_file, encrypted_file, seed_material)
    
    if encryption_result is None:
        print("Mã hóa thất bại!")
        return
    
    channels, framerate, sampwidth, original_hash = encryption_result
    print(f"Mã hóa thành công!")
    print(f"Channels: {channels}")
    print(f"Framerate: {framerate}")
    print(f"Sample Width: {sampwidth}")
    print(f"Original Hash: {original_hash}")
    
    print(f"\nĐang giải mã file '{encrypted_file}'...")
    # Giải mã file
    decryption_result = decrypt_audio_chaotic(
        encrypted_file, decrypted_file, seed_material, 
        channels, framerate, sampwidth, original_hash
    )
    
    if decryption_result:
        print(f"Giải mã thành công! File đã được lưu tại '{decrypted_file}'")
    else:
        print("Giải mã thất bại!")

if __name__ == "__main__":
    main() 