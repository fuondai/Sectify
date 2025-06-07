# -*- coding: utf-8 -*-
from functools import wraps
from flask import session, redirect, request, jsonify, current_app as app # Sử dụng current_app
import jwt

# --- Decorators Xác thực --- 

def token_required(func):
    """Decorator kiểm tra và xác thực JWT token trong session."""
    @wraps(func)
    def decorated(*args, **kwargs):
        token = session.get("token") # Lấy token từ session

        # Nếu không có token
        if not token:
            print("Yêu cầu token: Không tìm thấy token trong session.")
            # Nếu là API endpoint, trả về lỗi JSON
            if request.endpoint and ("api" in request.endpoint):
                 return jsonify({"error": "Yêu cầu token xác thực"}), 401
            # Nếu không phải API, chuyển hướng đến trang đăng nhập
            return redirect("/auth/login") # Giả định URL đăng nhập là /auth/login

        try:
            # Giải mã token sử dụng SECRET_KEY của app
            secret_key = app.config.get("SECRET_KEY")
            if not secret_key:
                 print("Lỗi: SECRET_KEY chưa được cấu hình.")
                 raise jwt.InvalidTokenError("Lỗi cấu hình server")
                 
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            # Lưu user_id từ payload vào session để sử dụng sau này
            session["user_id"] = payload.get("id")
            print(f"Token hợp lệ cho user_id: {session["user_id"]}")

        except jwt.ExpiredSignatureError: # Token hết hạn
            print("Yêu cầu token: Token đã hết hạn.")
            session.clear() # Xóa session khi token hết hạn
            if request.endpoint and ("api" in request.endpoint):
                 return jsonify({"error": "Token đã hết hạn"}), 401
            return redirect("/auth/login")
            
        except jwt.InvalidTokenError as e: # Token không hợp lệ
            print(f"Yêu cầu token: Token không hợp lệ. Lỗi: {e}")
            session.clear() # Xóa session khi token không hợp lệ
            if request.endpoint and ("api" in request.endpoint):
                 return jsonify({"error": "Token không hợp lệ"}), 401
            return redirect("/auth/login")
            
        except Exception as e: # Các lỗi khác
            print(f"Yêu cầu token: Lỗi không mong muốn khi giải mã token: {e}")
            session.clear()
            if request.endpoint and ("api" in request.endpoint):
                 return jsonify({"error": "Lỗi xác thực"}), 500
            return redirect("/auth/login")

        # Nếu token hợp lệ, thực thi hàm gốc
        return func(*args, **kwargs)
    return decorated

def login_required(func):
    """Decorator kiểm tra người dùng đã đăng nhập chưa (dựa vào user_id trong session)."""
    @wraps(func)
    def decorated(*args, **kwargs):
        # Kiểm tra sự tồn tại của user_id trong session (được đặt bởi token_required)
        if "user_id" in session:
            # Người dùng đã đăng nhập và có token hợp lệ
            return func(*args, **kwargs)
        else:
            # Người dùng chưa đăng nhập hoặc session không hợp lệ
            print("Yêu cầu đăng nhập: Không tìm thấy user_id trong session.")
            session.clear() # Xóa session không hợp lệ
            if request.endpoint and ("api" in request.endpoint):
                 return jsonify({"error": "Yêu cầu đăng nhập"}), 401
            return redirect("/auth/login") # Chuyển hướng đến trang đăng nhập
    return decorated

