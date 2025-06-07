# -*- coding: utf-8 -*-
import os
import wave
import numpy as np # Sử dụng numpy để tăng hiệu quả tính toán (ví dụ: XOR)
from hashlib import sha256

# --- Tham số cho Sơ đồ Hỗn loạn (Ví dụ: Logistic Map) ---
R_PARAM = 3.99 # Tham số r cho logistic map (giá trị này thường thể hiện hành vi hỗn loạn)
# Lưu ý: Logistic map là một ví dụ đơn giản, không đủ an toàn cho ứng dụng thực tế.
# Cần thay thế bằng sơ đồ hỗn loạn phức tạp hơn hoặc chuẩn mã hóa mạnh hơn.

def derive_initial_state(seed_material):
    """Tạo trạng thái ban đầu (x0) cho sơ đồ hỗn loạn từ seed_material bằng SHA-256.
    Việc sử dụng hash giúp phân tán và tăng tính khó đoán của trạng thái ban đầu.

    Args:
        seed_material (bytes): Dữ liệu dùng để tạo seed (ví dụ: từ mật khẩu + salt, hoặc ngẫu nhiên).

    Returns:
        float: Trạng thái ban đầu x0 trong khoảng (0, 1), không bao gồm 0 và 1.
    """
    # Băm seed_material bằng SHA-256 để tăng tính ngẫu nhiên và phân bố
    hasher = sha256()
    hasher.update(seed_material)
    hashed_seed = hasher.digest()
    # Lấy 8 byte đầu của hash chuyển thành số nguyên lớn
    int_val = int.from_bytes(hashed_seed[:8], byteorder="big")
    # Chuẩn hóa giá trị về khoảng [0, 1)
    x0 = (int_val / (2**64)) % 1.0
    # Đảm bảo x0 không phải là 0 hoặc 1 (các điểm cố định của logistic map, có thể làm giảm tính hỗn loạn)
    if x0 == 0.0:
        x0 = 0.01 # Giá trị thay thế nhỏ
    elif x0 == 1.0:
        x0 = 0.99 # Giá trị thay thế gần 1
    return x0

def generate_chaotic_keystream(x0, r, size):
    """Tạo chuỗi khóa (keystream) bằng sơ đồ hỗn loạn (Logistic Map).
    Keystream này sẽ được XOR với dữ liệu để mã hóa/giải mã.

    Args:
        x0 (float): Trạng thái ban đầu (từ derive_initial_state).
        r (float): Tham số của logistic map (R_PARAM).
        size (int): Kích thước (số byte) của keystream cần tạo.

    Returns:
        bytes: Chuỗi khóa được tạo, hoặc None nếu không tạo đủ trong giới hạn lặp.
    """
    keystream = bytearray() # Sử dụng bytearray để hiệu quả khi nối byte
    x = x0 # Giá trị lặp hiện tại, bắt đầu từ x0
    generated_bytes = 0
    iterations = 0
    # Giới hạn số lần lặp để tránh vòng lặp vô hạn nếu có vấn đề (ví dụ: x hội tụ)
    max_iterations = size * 10 # Giới hạn tương đối, có thể cần điều chỉnh

    # Vòng lặp tạo giá trị hỗn loạn và trích xuất byte
    while generated_bytes < size and iterations < max_iterations:
        # Công thức Logistic Map: x_next = r * x * (1 - x)
        x = r * x * (1 - x)
        try:
            # Chuyển giá trị float (64-bit) thành chuỗi byte
            float_bytes = np.float64(x).tobytes()
            # Trích xuất một phần byte từ biểu diễn float để làm keystream
            # Việc chọn byte nào (đầu, giữa, cuối) có thể ảnh hưởng đến tính ngẫu nhiên
            # Lấy 4 byte ở giữa là một lựa chọn phổ biến nhưng cần phân tích kỹ hơn.
            extracted = float_bytes[2:6] 
            keystream.extend(extracted)
            generated_bytes += len(extracted)
        except Exception as e:
            # Cảnh báo nếu có lỗi trong quá trình chuyển đổi
            print(f"Cảnh báo: Lỗi chuyển đổi giá trị hỗn loạn {x} thành byte: {e}")
        iterations += 1

    # Kiểm tra xem đã tạo đủ keystream chưa
    if generated_bytes < size:
        print(f"Cảnh báo: Tạo keystream dừng sớm sau {iterations} lần lặp. Cần: {size}, Tạo được: {generated_bytes}")
        return None # Trả về None nếu không đủ

    # Chỉ trả về số byte đúng bằng kích thước yêu cầu
    return bytes(keystream[:size])

def xor_encrypt_decrypt(data, keystream):
    """Thực hiện mã hóa/giải mã bằng phép XOR giữa dữ liệu và keystream.
    Đây là cơ chế cốt lõi của mã hóa dòng.

    Args:
        data (bytes): Dữ liệu cần mã hóa hoặc giải mã.
        keystream (bytes): Chuỗi khóa có độ dài ít nhất bằng data.

    Returns:
        bytes: Kết quả sau khi XOR (ciphertext hoặc plaintext).
    """
    if len(data) > len(keystream):
        raise ValueError("Lỗi XOR: Độ dài dữ liệu lớn hơn độ dài keystream.")

    # Sử dụng numpy để XOR hiệu quả hơn với dữ liệu lớn
    data_np = np.frombuffer(data, dtype=np.uint8)
    # Chỉ lấy phần keystream tương ứng với độ dài dữ liệu
    key_np = np.frombuffer(keystream[:len(data)], dtype=np.uint8)
    # Thực hiện phép XOR trên từng byte
    encrypted_np = np.bitwise_xor(data_np, key_np)
    return encrypted_np.tobytes()

def encrypt_audio_chaotic(input_path, output_path, seed_material):
    """Mã hóa tệp âm thanh WAV sử dụng mã hóa dòng hỗn loạn (Logistic Map).

    Args:
        input_path (str): Đường dẫn tệp WAV đầu vào.
        output_path (str): Đường dẫn lưu tệp dữ liệu đã mã hóa (không phải WAV).
        seed_material (bytes): Dữ liệu để tạo seed cho bộ tạo hỗn loạn.

    Returns:
        tuple: (channels, framerate, sampwidth, original_sha256_hash) nếu thành công, None nếu lỗi.
               original_sha256_hash (str): Hash SHA-256 của dữ liệu gốc để kiểm tra toàn vẹn khi giải mã.
    """
    try:
        # Đọc thông tin và dữ liệu tệp WAV gốc
        with wave.open(input_path, 'rb') as wf:
            channels = wf.getnchannels()
            framerate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            nframes = wf.getnframes()
            audio_data = wf.readframes(nframes) # Đọc toàn bộ dữ liệu frame âm thanh
            data_length = len(audio_data)
            print(f"Đã đọc dữ liệu âm thanh: {data_length} bytes")

        # Tính hash SHA-256 của dữ liệu gốc để kiểm tra toàn vẹn khi giải mã
        original_hash = sha256(audio_data).hexdigest()
        print(f"SHA256 dữ liệu gốc: {original_hash}")

        # Tạo trạng thái ban đầu từ seed_material
        x0 = derive_initial_state(seed_material)
        print(f"Đang tạo keystream hỗn loạn độ dài {data_length}...")
        # Tạo keystream có độ dài bằng dữ liệu âm thanh
        keystream = generate_chaotic_keystream(x0, R_PARAM, data_length)

        if keystream is None:
             print("Lỗi mã hóa Chaotic: Không thể tạo đủ keystream.")
             return None

        print("Đang mã hóa dữ liệu bằng XOR...")
        # Mã hóa dữ liệu bằng cách XOR với keystream
        encrypted_data = xor_encrypt_decrypt(audio_data, keystream)

        # Ghi dữ liệu đã mã hóa ra tệp đầu ra (dữ liệu thô)
        with open(output_path, 'wb') as ef:
            ef.write(encrypted_data)

        print(f"Tệp âm thanh '{input_path}' đã mã hóa thành công (chaotic) sang '{output_path}'.")
        # Trả về metadata và hash gốc để lưu trữ
        return channels, framerate, sampwidth, original_hash

    except FileNotFoundError:
        print(f"Lỗi mã hóa Chaotic: Không tìm thấy tệp âm thanh đầu vào tại '{input_path}'")
        return None
    except wave.Error as e:
        print(f"Lỗi mã hóa Chaotic: Lỗi khi đọc tệp WAV '{input_path}': {e}")
        return None
    except Exception as e:
        print(f"Lỗi mã hóa Chaotic: Lỗi không mong muốn xảy ra: {e}")
        return None

def decrypt_audio_chaotic(input_path, output_path, seed_material, channels, framerate, sampwidth, expected_original_hash):
    """Giải mã tệp âm thanh được mã hóa bằng mã hóa dòng hỗn loạn và kiểm tra tính toàn vẹn.

    Args:
        input_path (str): Đường dẫn tệp dữ liệu đã mã hóa.
        output_path (str): Đường dẫn lưu tệp WAV đã giải mã.
        seed_material (bytes): Dữ liệu seed (phải giống hệt lúc mã hóa).
        channels (int): Số kênh âm thanh (từ metadata).
        framerate (int): Tốc độ khung hình (từ metadata).
        sampwidth (int): Độ rộng mẫu (từ metadata).
        expected_original_hash (str): Hash SHA-256 của dữ liệu gốc (từ metadata).

    Returns:
        bool: True nếu giải mã và kiểm tra toàn vẹn thành công, False nếu ngược lại.
    """
    try:
        # Đọc dữ liệu đã mã hóa từ tệp
        with open(input_path, 'rb') as ef:
            encrypted_data = ef.read()
            data_length = len(encrypted_data)
            print(f"Đã đọc dữ liệu mã hóa: {data_length} bytes")

        # Tạo lại trạng thái ban đầu từ seed_material (phải giống hệt lúc mã hóa)
        x0 = derive_initial_state(seed_material)
        print(f"Đang tạo keystream hỗn loạn độ dài {data_length} để giải mã...")
        # Tạo lại keystream giống hệt lúc mã hóa
        keystream = generate_chaotic_keystream(x0, R_PARAM, data_length)

        if keystream is None:
             print("Lỗi giải mã Chaotic: Không thể tạo đủ keystream.")
             # Đảm bảo không để lại tệp đầu ra nếu keystream lỗi
             if os.path.exists(output_path):
                 try:
                     os.remove(output_path)
                 except OSError as rm_err:
                     print(f"Cảnh báo: Không thể xóa tệp đầu ra '{output_path}' khi keystream lỗi: {rm_err}")
             return False

        print("Đang giải mã dữ liệu bằng XOR...")
        # Giải mã bằng cách XOR lại với cùng keystream
        decrypted_data = xor_encrypt_decrypt(encrypted_data, keystream)

        # --- Kiểm tra Tính toàn vẹn --- 
        # Tính hash của dữ liệu vừa giải mã
        decrypted_hash = sha256(decrypted_data).hexdigest()
        print(f"SHA256 dữ liệu giải mã: {decrypted_hash}")
        # So sánh với hash gốc được lưu trữ
        if decrypted_hash != expected_original_hash:
            print(f"KIỂM TRA TOÀN VẸN THẤT BẠI! Hash không khớp. Mong đợi: {expected_original_hash}")
            # Đảm bảo không để lại tệp đầu ra nếu hash không khớp
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError as rm_err:
                    print(f"Cảnh báo: Không thể xóa tệp đầu ra '{output_path}' khi hash không khớp: {rm_err}")
            return False
        else:
            print("KIỂM TRA TOÀN VẸN THÀNH CÔNG.")
            # Chỉ ghi dữ liệu đã giải mã ra tệp WAV nếu kiểm tra toàn vẹn thành công
            with wave.open(output_path, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(decrypted_data)
            print(f"Tệp mã hóa '{input_path}' đã giải mã thành công (chaotic) sang '{output_path}'.")
            return True

    except FileNotFoundError:
        print(f"Lỗi giải mã Chaotic: Không tìm thấy tệp mã hóa đầu vào tại '{input_path}'")
        return False
    except Exception as e:
        print(f"Lỗi giải mã Chaotic: Lỗi không mong muốn xảy ra: {e}")
        # Đảm bảo không để lại tệp đầu ra nếu có lỗi khác
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as rm_err:
                print(f"Cảnh báo: Không thể xóa tệp đầu ra '{output_path}' khi có lỗi giải mã: {rm_err}")
        return False

