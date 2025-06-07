#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import wave
import struct

def create_sine_wave(filename, duration=3, freq=440.0, sample_rate=44100, amplitude=32767):
    """Tạo một file WAV đơn giản với âm thanh sine wave.
    
    Args:
        filename: Tên file WAV đầu ra
        duration: Thời lượng âm thanh (giây)
        freq: Tần số âm thanh (Hz)
        sample_rate: Tốc độ lấy mẫu (Hz)
        amplitude: Biên độ âm thanh (16-bit: max 32767)
    """
    # Tạo mảng thời gian
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Tạo sine wave
    tone = np.sin(2 * np.pi * freq * t) * amplitude
    
    # Chuyển đổi thành số nguyên 16-bit
    tone_int = tone.astype(np.int16)
    
    # Tạo file WAV
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 2 bytes = 16 bit
        wf.setframerate(sample_rate)
        
        # Ghi dữ liệu
        for sample in tone_int:
            wf.writeframes(struct.pack('h', sample))
    
    print(f"Đã tạo file WAV: {filename}")

if __name__ == "__main__":
    # Tạo một vài file WAV khác nhau
    create_sine_wave("test_files/test_440hz.wav", freq=440)  # A4 (La)
    create_sine_wave("test_files/test_523hz.wav", freq=523.25)  # C5 (Đô)
    create_sine_wave("test_files/test_660hz.wav", freq=659.25)  # E5 (Mi) 