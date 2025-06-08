# -*- coding: utf-8 -*-
from flask import request, session, redirect, render_template, jsonify, send_file, abort, Response
from . import audio # Import blueprint instance từ __init__.py cùng cấp
import os
import io
import uuid
from datetime import datetime
import json
import mimetypes
from werkzeug.utils import secure_filename
from src import db # Import biến db từ __init__.py
from src.utils.decorators import login_required # Import decorator login_required
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib
import base64
import re

def encrypt_data(data, key):
    """Mã hóa dữ liệu sử dụng AES-256-CBC"""
    # Tạo khóa từ key người dùng
    key = hashlib.sha256(key.encode()).digest()
    # Tạo IV ngẫu nhiên
    iv = get_random_bytes(16)
    # Tạo đối tượng mã hóa
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # Thêm padding cho dữ liệu
    block_size = AES.block_size
    if isinstance(data, str):
        data = data.encode('utf-8')
    padding = block_size - len(data) % block_size
    data += bytes([padding]) * padding
    # Mã hóa dữ liệu
    encrypted_data = cipher.encrypt(data)
    # Trả về IV + dữ liệu đã mã hóa dướidạng base64
    return base64.b64encode(iv + encrypted_data)

def decrypt_data(encrypted_data, key):
    """Giải mã dữ liệu đã được mã hóa bằng AES-256-CBC"""
    try:
        # Giải mã base64
        encrypted_data = base64.b64decode(encrypted_data)
        # Tách IV và dữ liệu
        iv = encrypted_data[:16]
        encrypted_data = encrypted_data[16:]
        # Tạo khóa từ key người dùng
        key = hashlib.sha256(key.encode()).digest()
        # Tạo đối tượng giải mã
        cipher = AES.new(key, AES.MODE_CBC, iv)
        # Giải mã dữ liệu
        data = cipher.decrypt(encrypted_data)
        # Xóa padding
        padding = data[-1]
        return data[:-padding]
    except Exception as e:
        print(f"Lỗi khi giải mã: {str(e)}")
        return None

# Sử dụng decorator của blueprint (@audio.route) thay vì @app.route
# để đăng ký các route này với blueprint 'audio'

@audio.route("/library")
@login_required
def library():
    """Hiển thị trang thư viện âm thanh.
    Yêu cầu người dùng đã đăng nhập.
    """
    return render_template("audio/library.html")

@audio.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Xử lý tải lên tệp âm thanh.
    GET: Hiển thị form tải lên.
    POST: Xử lý yêu cầu tải lên.
    Yêu cầu người dùng đã đăng nhập.
    """
    if request.method == "GET":
        return render_template("audio/upload.html")
    
    # Xử lý POST request (tải lên tệp)
    # Kiểm tra tệp được tải lên, chấp nhận cả 'audio_file' (frontend) và 'file' (curl/test)
    upload_key = None
    if "audio_file" in request.files:
        upload_key = "audio_file"
    elif "file" in request.files:
        upload_key = "file"

    if not upload_key:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files[upload_key]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    # Kiểm tra loại tệp (chỉ chấp nhận .wav, .mp3, .ogg, .flac)
    allowed_extensions = {"wav", "mp3", "ogg", "flac"}
    filename = file.filename
    if "." not in filename or filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Only .wav, .mp3, .ogg, .flac files are allowed"}), 400
    
    # Lưu tệp vào thư mục tạm (hoặc lưu trữ trong memory)
    # Trong môi trường production, bạn nên lưu vào cloud storage hoặc thư mục an toàn
    try:
        # Tạo ID duy nhất cho tệp
        file_id = str(uuid.uuid4())
        
        # Đọc nội dung tệp
        file_content = file.read()
        
        # Lưu thông tin tệp vào database
        audio_file = {
            "id": file_id,
            "name": secure_filename(file.filename),
            "user_id": session.get("user_id"),
            "status": "original",  # original, encrypted, decrypted
            "upload_date": datetime.now(),
            "size": len(file_content),
            "content": file_content,  # Lưu nội dung tệp dướidạng binary data
            "metadata": {}  # Metadata sẽ được cập nhật khi mã hóa/giải mã
        }
        
        # Chèn vào database
        db["audio_files"].insert_one(audio_file)
        
        return jsonify({
            "success": True,
            "file_id": file_id,
            "message": "File uploaded successfully"
        }), 200
    
    except Exception as e:
        print(f"Error uploading file: {e}")
        return jsonify({"error": f"Failed to upload file: {str(e)}"}), 500

@audio.route("/files")
@login_required
def get_files():
    """Lấy danh sách tệp âm thanh của người dùng hiện tại.
    Yêu cầu người dùng đã đăng nhập.
    """
    try:
        # Lấy danh sách tệp từ database
        user_files = list(db["audio_files"].find({"user_id": session.get("user_id")}))
        
        # Chuyển đổi ObjectId thành string và loại bỏ nội dung tệp (để giảm kích thước response)
        for file in user_files:
            file["_id"] = str(file["_id"])
            # Loại bỏ mọi trường có kiểu bytes (ví dụ: content, original_content)
            for k in list(file.keys()):
                if isinstance(file[k], bytes):
                    del file[k]
            # Chuyển datetime thành string
            if isinstance(file.get("upload_date"), datetime):
                file["upload_date"] = file["upload_date"].isoformat()
        
        return jsonify({
            "success": True,
            "files": user_files
        }), 200
    
    except Exception as e:
        print(f"Error getting files: {e}")
        return jsonify({"error": f"Failed to retrieve files: {str(e)}"}), 500

@audio.route("/encrypt/<file_id>/<algorithm>", methods=["POST"])
@login_required
def encrypt_audio(file_id, algorithm):
    """Mã hóa tệp âm thanh.
    Yêu cầu người dùng đã đăng nhập.
    file_id: ID của tệp cần mã hóa
    algorithm: Thuật toán mã hóa (aes hoặc chaotic)
    """
    # Kiểm tra algorithm
    if algorithm not in ["aes"]:  # Tạm thởi chỉ hỗ trợ AES
        return jsonify({"error": "Only AES encryption is currently supported"}), 400
    
    try:
        # Lấy key mã hóa từ form
        encryption_key = request.form.get('encryption_key')
        # Kiểm tra độ dài khóa AES
        if len(encryption_key) not in (16, 24, 32):
            return jsonify({"error": "Encryption key must be 16, 24, or 32 characters long"}), 400
        if not encryption_key:
            return jsonify({"error": "Encryption key is required"}), 400
            
        # Lấy tệp từ database
        audio_file = db["audio_files"].find_one({
            "id": file_id,
            "user_id": session.get("user_id")
        })
        
        if not audio_file:
            return jsonify({"error": "File not found or access denied"}), 404
        
        # Kiểm tra trạng thái tệp
        if audio_file.get("status") == "encrypted":
            return jsonify({"error": "File is already encrypted"}), 400
        
        # Mã hóa nội dung tệp
        encrypted_content = encrypt_data(audio_file["content"], encryption_key)
        
        # Tạo metadata mã hóa
        encryption_metadata = {
            "algorithm": algorithm,
            "encrypted_at": datetime.now().isoformat(),
            "original_size": len(audio_file["content"]),
            "encrypted_size": len(encrypted_content)
        }
        
        # Lưu bản gốc nếu chưa có
        if "original_content" not in audio_file:
            db["audio_files"].update_one(
                {"id": file_id},
                {"$set": {"original_content": audio_file["content"]}}
            )
        
        # Cập nhật tệp trong database
        db["audio_files"].update_one(
            {"id": file_id},
            {"$set": {
                "status": "encrypted",
                "content": encrypted_content,
                "metadata": encryption_metadata,
                "encryption_key": hashlib.sha256(encryption_key.encode()).hexdigest()  # Lưu hash của key để kiểm tra sau này
            }}
        )
        
        return jsonify({
            "success": True,
            "message": f"File encrypted successfully using {algorithm} algorithm"
        }), 200
    
    except Exception as e:
        print(f"Error encrypting file: {e}")
        return jsonify({"error": f"Failed to encrypt file: {str(e)}"}), 500

@audio.route("/decrypt/<file_id>", methods=["POST"])
@login_required
def decrypt_audio(file_id):
    """Giải mã tệp âm thanh.
    Yêu cầu người dùng đã đăng nhập.
    file_id: ID của tệp cần giải mã
    """
    try:
        # Lấy key giải mã từ form
        decryption_key = request.form.get('decryption_key')
        # Kiểm tra độ dài khóa AES
        if len(decryption_key) not in (16, 24, 32):
            return jsonify({"error": "Decryption key must be 16, 24, or 32 characters long"}), 400
        if not decryption_key:
            return jsonify({"error": "Decryption key is required"}), 400
            
        # Lấy tệp từ database
        audio_file = db["audio_files"].find_one({
            "id": file_id,
            "user_id": session.get("user_id")
        })
        
        if not audio_file:
            return jsonify({"error": "File not found or access denied"}), 404
        
        # Kiểm tra trạng thái tệp
        if audio_file.get("status") != "encrypted":
            return jsonify({"error": "File is not encrypted"}), 400
        
        # Kiểm tra key giải mã
        key_hash = hashlib.sha256(decryption_key.encode()).hexdigest()
        if audio_file.get("encryption_key") != key_hash:
            return jsonify({"error": "Incorrect decryption key"}), 401
        
        # Giải mã nội dung tệp
        decrypted_content = decrypt_data(audio_file["content"], decryption_key)
        if not decrypted_content:
            return jsonify({"error": "Failed to decrypt file with the provided key"}), 400
        
        # Cập nhật tệp trong database
        db["audio_files"].update_one(
            {"id": file_id},
            {"$set": {
                "status": "decrypted",
                "content": decrypted_content,
                "metadata.decrypted_at": datetime.now().isoformat()
            }}
        )
        
        return jsonify({
            "success": True,
            "message": "File decrypted successfully"
        }), 200
    
    except Exception as e:
        print(f"Error decrypting file: {e}")
        return jsonify({"error": f"Failed to decrypt file: {str(e)}"}), 500

@audio.route("/download/<file_id>/<file_type>")
@login_required
def download_audio(file_id, file_type):
    """Tải xuống tệp âm thanh.
    Yêu cầu người dùng đã đăng nhập.
    file_id: ID của tệp cần tải xuống
    file_type: Loại tệp (original, encrypted, decrypted)
    """
    # Kiểm tra file_type
    if file_type not in ["original", "encrypted", "decrypted"]:
        abort(400, "Invalid file type")
    
    try:
        # Lấy tệp từ database
        audio_file = db["audio_files"].find_one({
            "id": file_id,
            "user_id": session.get("user_id")
        })
        
        if not audio_file:
            abort(404, "File not found")
        
        # Kiểm tra quyền truy cập
        if audio_file.get("user_id") != session.get("user_id"):
            abort(403, "Access denied")
        
        # Kiểm tra trạng thái tệp
        if audio_file.get("status") != file_type and file_type != "original":
            abort(400, f"File is not in {file_type} state")
        
        # Lấy nội dung tệp
        file_content = None
        if file_type == "original" and "original_content" in audio_file:
            file_content = audio_file["original_content"]
        else:
            file_content = audio_file.get("content")
            
        if not file_content:
            abort(404, "File content not found")
        
        # Xác định mimetype dựa trên phần mở rộng file
        filename = audio_file.get("name", "audio")
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        # Ánh xạ phần mở rộng sang mimetype
        mime_map = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.aac': 'audio/aac',
            '.m4a': 'audio/mp4',
            '.wma': 'audio/x-ms-wma'
        }
        
        mimetype = mime_map.get(ext, 'application/octet-stream')
        
        # Tạo tên file tải xuống
        if file_type != "original":
            name, _ = os.path.splitext(filename)
            filename = f"{name}_{file_type}{ext}"
        
        # Tạo response với các header bảo mật
        response = send_file(
            io.BytesIO(file_content),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
        # Thêm các header bảo mật
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        # Đặt thởi gian cache ngắn cho file nhạy cảm
        if file_type != "original":
            response.cache_control.no_cache = True
            response.cache_control.no_store = True
            response.cache_control.must_revalidate = True
            response.cache_control.max_age = 0
        
        return response
    
    except Exception as e:
        print(f"Error downloading file: {e}")
        abort(500, "Internal server error")

@audio.route("/player")
@login_required
def player_page():
    """Hiển thị trang phát nhạc độc lập.
    Yêu cầu người dùng đã đăng nhập.
    
    Returns:
        Trang phát nhạc player.html
    """
    return render_template("audio/player.html")

# =====================================================================
# Stream audio
# =====================================================================

@audio.route("/stream/<file_id>")
@login_required
def stream_audio(file_id):
    """Phát trực tuyến tệp âm thanh.
    
    Browser audio element sẽ gửi header Range khi cần phát một phần tệp.
    Hàm này hỗ trợ cả request đầy đủ và request theo Range.
    Chỉ cho phép người dùng hiện tại truy cập tệp của chính họ.
    """
    try:
        # Lấy tệp từ database
        audio_file = db["audio_files"].find_one({
            "id": file_id,
            "user_id": session.get("user_id")
        })
        
        if not audio_file:
            abort(404, "File not found")
        
        # Ưu tiên nội dung đã giải mã, sau đó tới nội dung gốc
        file_content = audio_file.get("content")
        if not file_content and "original_content" in audio_file:
            file_content = audio_file["original_content"]
        
        if not file_content:
            abort(404, "File content not found")
        
        # Xác định mimetype
        filename = audio_file.get("name", "audio")
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        mime_map = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.aac': 'audio/aac',
            '.m4a': 'audio/mp4',
            '.wma': 'audio/x-ms-wma'
        }
        mimetype = mime_map.get(ext, 'application/octet-stream')
        
        # Hỗ trợ header Range cho streaming
        range_header = request.headers.get('Range', None)
        if range_header:
            # Ví dụ header: Range: bytes=0-1023
            byte1, byte2 = 0, None
            m = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if m:
                byte1 = int(m.group(1))
                if m.group(2):
                    byte2 = int(m.group(2))
            
            data_length = len(file_content)
            if byte2 is None or byte2 >= data_length:
                byte2 = data_length - 1
            
            if byte1 >= data_length:
                # Range vượt quá độ dài tệp
                abort(416, "Requested Range Not Satisfiable")
            
            sliced_data = file_content[byte1:byte2 + 1]
            rv = Response(sliced_data, 206, mimetype=mimetype, direct_passthrough=True)
            rv.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{data_length}')
            rv.headers.add('Accept-Ranges', 'bytes')
            rv.headers.add('Content-Length', str(byte2 - byte1 + 1))
            return rv
        
        # Nếu không có Range header -> trả toàn bộ tệp
        return send_file(
            io.BytesIO(file_content),
            mimetype=mimetype,
            as_attachment=False,
            download_name=filename,
            conditional=True  # Cho phép Flask tự thêm Last-Modified, etc.
        )
    
    except Exception as e:
        print(f"Error streaming audio: {e}")
        abort(500, "Internal server error")

# Xóa tệp âm thanh
@audio.route("/delete/<file_id>", methods=["DELETE"])
@login_required
def delete_audio(file_id):
    try:
        # Lấy tệp từ database
        audio_file = db["audio_files"].find_one({
            "id": file_id,
            "user_id": session.get("user_id")
        })
        
        if not audio_file:
            return jsonify({"error": "File not found or access denied"}), 404
        
        # Xóa tệp khỏi database
        db["audio_files"].delete_one({"id": file_id})
        
        return jsonify({
            "success": True,
            "message": "File deleted successfully"
        }), 200
    
    except Exception as e:
        print(f"Error deleting file: {e}")
        return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500

# Thống kê số lượng bài hát
@audio.route("/stats")
@login_required
def audio_stats():
    user_id = session.get("user_id")
    total = db["audio_files"].count_documents({"user_id": user_id})
    encrypted = db["audio_files"].count_documents({"user_id": user_id, "status": "encrypted"})
    decrypted = db["audio_files"].count_documents({"user_id": user_id, "status": "decrypted"})
    return jsonify({"success": True, "stats": {"total": total, "encrypted": encrypted, "decrypted": decrypted}}), 200

# Lấy các bài hát mới tải lên
@audio.route("/recent")
@login_required
def audio_recent():
    user_id = session.get("user_id")
    files = list(db["audio_files"].find({"user_id": user_id}).sort("upload_date", -1).limit(4))
    tracks = []
    for file in files:
        tracks.append({
            'id': file['id'], 'name': file['name'], 'status': file.get('status', 'original')
        })
    return jsonify({"success": True, "tracks": tracks}), 200
