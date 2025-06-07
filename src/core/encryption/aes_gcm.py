# -*- coding: utf-8 -*-
import os
import wave
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag # Import exception để xử lý lỗi tag xác thực

# --- Hằng số --- 
AES_KEY_SIZE = 32  # Kích thước khóa AES: 32 bytes = 256 bits
NONCE_SIZE = 12    # Kích thước Nonce: 12 bytes = 96 bits (khuyến nghị cho GCM)

def generate_key_nonce():
    """Tạo khóa AES và Nonce ngẫu nhiên, an toàn.
    Sử dụng os.urandom để đảm bảo tính ngẫu nhiên mật mã.
    """
    # Sử dụng os.urandom để tạo dữ liệu ngẫu nhiên từ nguồn của hệ điều hành
    key = os.urandom(AES_KEY_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    return key, nonce

def encrypt_audio(input_path, output_path):
    """Mã hóa tệp âm thanh WAV sử dụng AES-256-GCM.

    Args:
        input_path (str): Đường dẫn đến tệp âm thanh WAV đầu vào.
        output_path (str): Đường dẫn để lưu tệp dữ liệu đã mã hóa (không phải WAV).

    Returns:
        tuple: (key, nonce, channels, framerate, sampwidth) nếu thành công, None nếu lỗi.
               key (bytes): Khóa AES đã tạo (cần lưu trữ an toàn).
               nonce (bytes): Nonce đã tạo (cần lưu trữ cùng dữ liệu mã hóa).
               channels (int): Số kênh âm thanh (metadata).
               framerate (int): Tốc độ khung hình âm thanh (metadata).
               sampwidth (int): Độ rộng mẫu âm thanh (bytes) (metadata).
    """
    try:
        # Đọc thuộc tính và dữ liệu của tệp âm thanh WAV gốc
        with wave.open(input_path, 'rb') as wf:
            channels = wf.getnchannels()
            framerate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            nframes = wf.getnframes()
            audio_data = wf.readframes(nframes) # Đọc toàn bộ dữ liệu frame âm thanh

        # Tạo khóa và nonce mới, duy nhất cho mỗi lần mã hóa
        key, nonce = generate_key_nonce()

        # Khởi tạo đối tượng mã hóa AESGCM với khóa đã tạo
        aesgcm = AESGCM(key)
        # Mã hóa dữ liệu âm thanh. AES-GCM cung cấp cả mã hóa và xác thực.
        # `None` ở đây nghĩa là không có dữ liệu liên kết bổ sung (AAD).
        encrypted_data = aesgcm.encrypt(nonce, audio_data, None)

        # Ghi dữ liệu đã mã hóa (ciphertext + tag) ra tệp đầu ra.
        # Lưu ý: Đây là dữ liệu mã hóa thô, không phải định dạng WAV.
        # Metadata (channels, framerate, sampwidth) cùng với key và nonce
        # cần được lưu trữ riêng biệt và an toàn để có thể giải mã sau này.
        with open(output_path, 'wb') as ef:
            ef.write(encrypted_data)

        print(f"Tệp âm thanh '{input_path}' đã được mã hóa thành công (AES-GCM) sang '{output_path}'.")
        # Trả về key, nonce và metadata để ứng dụng có thể lưu trữ chúng
        return key, nonce, channels, framerate, sampwidth

    except FileNotFoundError:
        print(f"Lỗi mã hóa AES: Không tìm thấy tệp âm thanh đầu vào tại '{input_path}'")
        return None
    except wave.Error as e:
        print(f"Lỗi mã hóa AES: Lỗi khi đọc tệp WAV '{input_path}': {e}")
        return None
    except Exception as e:
        print(f"Lỗi mã hóa AES: Lỗi không mong muốn xảy ra: {e}")
        return None

def decrypt_audio(input_path, output_path, key, nonce, channels, framerate, sampwidth):
    """Giải mã tệp âm thanh đã mã hóa bằng AES-256-GCM và lưu dưới dạng WAV.

    Args:
        input_path (str): Đường dẫn đến tệp dữ liệu đã mã hóa.
        output_path (str): Đường dẫn để lưu tệp âm thanh WAV đã giải mã.
        key (bytes): Khóa AES đã sử dụng để mã hóa (phải chính xác).
        nonce (bytes): Nonce đã sử dụng để mã hóa (phải chính xác).
        channels (int): Số kênh âm thanh (lấy từ metadata đã lưu).
        framerate (int): Tốc độ khung hình (lấy từ metadata đã lưu).
        sampwidth (int): Độ rộng mẫu (lấy từ metadata đã lưu).

    Returns:
        bool: True nếu giải mã và ghi tệp WAV thành công, False nếu có lỗi.
    """
    try:
        # Đọc dữ liệu đã mã hóa từ tệp
        with open(input_path, 'rb') as ef:
            encrypted_data = ef.read()

        # Khởi tạo đối tượng giải mã AESGCM với khóa
        aesgcm = AESGCM(key)
        # Giải mã dữ liệu bằng nonce. AESGCM sẽ tự động kiểm tra tính toàn vẹn (authenticity tag).
        # Nếu dữ liệu bị thay đổi hoặc key/nonce sai, sẽ ném ra exception InvalidTag.
        decrypted_data = aesgcm.decrypt(nonce, encrypted_data, None)

        # Ghi dữ liệu đã giải mã (plaintext) ra tệp WAV mới, sử dụng metadata đã cung cấp
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(framerate)
            wf.writeframes(decrypted_data)

        print(f"Tệp mã hóa '{input_path}' đã được giải mã thành công (AES-GCM) sang '{output_path}'.")
        return True

    except InvalidTag:
        # Lỗi này xảy ra khi tag xác thực không khớp -> dữ liệu đã bị thay đổi hoặc key/nonce sai.
        print(f"Lỗi giải mã AES: Dữ liệu không hợp lệ hoặc bị thay đổi (Invalid Tag). Input: {input_path}")
        # Đảm bảo không để lại tệp đầu ra nếu giải mã thất bại
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as rm_err:
                print(f"Cảnh báo: Không thể xóa tệp đầu ra '{output_path}' khi có lỗi InvalidTag: {rm_err}")
        return False
    except FileNotFoundError:
        print(f"Lỗi giải mã AES: Không tìm thấy tệp mã hóa đầu vào tại '{input_path}'")
        return False
    except Exception as e:
        # Bắt các lỗi tiềm ẩn khác (ví dụ: lỗi ghi file WAV)
        print(f"Lỗi giải mã AES: Lỗi không mong muốn xảy ra: {e}")
        # Đảm bảo không để lại tệp đầu ra nếu có lỗi
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as rm_err:
                print(f"Cảnh báo: Không thể xóa tệp đầu ra '{output_path}' khi có lỗi giải mã khác: {rm_err}")
        return False

# Phần ví dụ sử dụng đã được comment lại, logic này sẽ được tích hợp vào ứng dụng Flask.

