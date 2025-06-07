# -*- coding: utf-8 -*-
import os
import json
from flask import current_app
from werkzeug.utils import secure_filename

# Lấy đường dẫn lưu trữ an toàn từ cấu hình app hiện tại
# Lưu ý: Cần app context để truy cập current_app.config
# SECURE_STORAGE_PATH = current_app.config.get("SECURE_STORAGE_PATH")
# -> Không thể đặt ở đây vì cần app context. Sẽ lấy trong hàm.

def get_secure_path(filename):
    """Tạo đường dẫn đầy đủ và an toàn cho một tệp trong thư mục lưu trữ.

    Args:
        filename (str): Tên tệp gốc.

    Returns:
        str: Đường dẫn tuyệt đối, an toàn đến tệp trong thư mục lưu trữ.
             Trả về None nếu không có app context hoặc cấu hình.
    """
    if not current_app:
        print("Error: Application context is required to get secure storage path.")
        return None
        
    storage_path = current_app.config.get("SECURE_STORAGE_PATH")
    if not storage_path:
        print("Error: SECURE_STORAGE_PATH is not configured in the application.")
        return None
        
    # Đảm bảo tên tệp an toàn
    safe_filename = secure_filename(filename)
    return os.path.join(storage_path, safe_filename)

def save_encryption_metadata(base_filename, metadata):
    """Lưu metadata mã hóa vào tệp JSON.

    Args:
        base_filename (str): Tên tệp gốc (không có phần mở rộng) để tạo tên tệp metadata.
        metadata (dict): Dictionary chứa metadata cần lưu (key_hex, nonce_hex, etc.).

    Returns:
        str: Đường dẫn đến tệp metadata đã lưu, hoặc None nếu lỗi.
    """
    metadata_filename = f"{base_filename}_metadata.json"
    metadata_path = get_secure_path(metadata_filename)
    
    if not metadata_path:
        return None
        
    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
        print(f"Encryption metadata saved to: {metadata_path}")
        return metadata_path
    except IOError as e:
        print(f"Error saving encryption metadata to {metadata_path}: {e}")
        return None
    except TypeError as e:
        print(f"Error serializing metadata to JSON: {e}")
        return None

def load_encryption_metadata(base_filename):
    """Tải metadata mã hóa từ tệp JSON.

    Args:
        base_filename (str): Tên tệp gốc (không có phần mở rộng) để tìm tệp metadata.

    Returns:
        dict: Dictionary chứa metadata đã tải, hoặc None nếu lỗi hoặc không tìm thấy.
    """
    metadata_filename = f"{base_filename}_metadata.json"
    metadata_path = get_secure_path(metadata_filename)
    
    if not metadata_path:
        return None
        
    if not os.path.exists(metadata_path):
        print(f"Encryption metadata file not found: {metadata_path}")
        return None
        
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        print(f"Encryption metadata loaded from: {metadata_path}")
        # Validate cơ bản (ví dụ: kiểm tra các key cần thiết)
        required_keys = ["key_hex", "nonce_hex", "channels", "framerate", "sampwidth", "algorithm"]
        if metadata.get("algorithm") == "chaotic":
             required_keys = ["seed_hex", "channels", "framerate", "sampwidth", "original_hash", "algorithm"]
             
        if not all(key in metadata for key in required_keys):
             print(f"Warning: Metadata file {metadata_path} is missing required keys.")
             # Có thể trả về None hoặc raise lỗi tùy theo yêu cầu
             # return None 
             
        return metadata
    except IOError as e:
        print(f"Error loading encryption metadata from {metadata_path}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from metadata file {metadata_path}: {e}")
        return None

# Có thể thêm các hàm tiện ích khác liên quan đến lưu trữ ở đây
# Ví dụ: hàm xóa tệp an toàn, hàm kiểm tra sự tồn tại, etc.

