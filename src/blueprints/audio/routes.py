# -*- coding: utf-8 -*-
from flask import request, session, redirect, render_template, jsonify, send_file, abort
from . import audio # Import blueprint instance từ __init__.py cùng cấp
import os
import io
import uuid
from datetime import datetime
import json
from werkzeug.utils import secure_filename
from src import db # Import biến db từ __init__.py
from src.utils.decorators import login_required # Import decorator login_required

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
    # Kiểm tra tệp được tải lên
    if "audio_file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files["audio_file"]
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
            "content": file_content,  # Lưu nội dung tệp dưới dạng binary data
            "metadata": {}  # Metadata sẽ được cập nhật khi mã hóa/giải mã
        }
        
        # Chèn vào database
        db["audio_files"].insert_one(audio_file)
        
        return jsonify({
            "success": True,
            "file_id": file_id,
            "message": "File uploaded successfully"
        }), 201
    
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
            if "content" in file:
                del file["content"]
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
    if algorithm not in ["aes", "chaotic"]:
        return jsonify({"error": "Invalid algorithm. Use 'aes' or 'chaotic'"}), 400
    
    try:
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
        
        # TODO: Thực hiện mã hóa tệp
        # Đây là nơi bạn sẽ thêm logic mã hóa thực tế, sử dụng module core/encryption
        
        # Mã giả để mô phỏng mã hóa (cần được thay thế bằng mã hóa thực tế)
        encrypted_content = audio_file.get("content")  # Giả vờ mã hóa
        encryption_metadata = {
            "algorithm": algorithm,
            "encrypted_at": datetime.now(),
            # Thêm các metadata khác như key, nonce, v.v.
        }
        
        # Cập nhật tệp trong database
        db["audio_files"].update_one(
            {"id": file_id},
            {"$set": {
                "status": "encrypted",
                "content": encrypted_content,
                "metadata": encryption_metadata
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
        
        # TODO: Thực hiện giải mã tệp
        # Đây là nơi bạn sẽ thêm logic giải mã thực tế, sử dụng module core/encryption
        
        # Mã giả để mô phỏng giải mã (cần được thay thế bằng giải mã thực tế)
        decrypted_content = audio_file.get("content")  # Giả vờ giải mã
        
        # Cập nhật tệp trong database
        db["audio_files"].update_one(
            {"id": file_id},
            {"$set": {
                "status": "decrypted",
                "content": decrypted_content,
                # Giữ lại metadata để có thể mã hóa lại nếu cần
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
        abort(400)
    
    try:
        # Lấy tệp từ database
        audio_file = db["audio_files"].find_one({
            "id": file_id,
            "user_id": session.get("user_id")
        })
        
        if not audio_file:
            abort(404)
        
        # Kiểm tra trạng thái tệp
        if audio_file.get("status") != file_type and file_type != "original":
            abort(400)
        
        # Lấy nội dung tệp
        file_content = audio_file.get("content")
        if not file_content:
            abort(404)
        
        # Tạo tên tệp tải xuống
        filename = audio_file.get("name", "audio.wav")
        if file_type != "original":
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{file_type}{ext}"
        
        # Trả về tệp
        return send_file(
            io.BytesIO(file_content),
            mimetype="audio/wav",  # TODO: Cần xác định đúng mimetype dựa trên loại tệp
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        print(f"Error downloading file: {e}")
        abort(500)

@audio.route("/player")
@login_required
def player_page():
    """Hiển thị trang phát nhạc độc lập.
    Yêu cầu người dùng đã đăng nhập.
    
    Returns:
        Trang phát nhạc player.html
    """
    return render_template("audio/player.html")
