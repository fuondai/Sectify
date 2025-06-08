# -*- coding: utf-8 -*-
from flask import request, session, redirect, render_template, jsonify, current_app
from . import auth # Import blueprint instance từ __init__.py cùng cấp
from .models import User # Import lớp User từ models.py cùng cấp
# Sử dụng decorator của blueprint (@auth.route) thay vì @app.route
# để đăng ký các route này với blueprint 'auth'

@auth.route("/login", methods=["GET", "POST"])
def login():
    """Endpoint xử lý yêu cầu đăng nhập.
    GET: Hiển thị form đăng nhập.
    POST: Xử lý yêu cầu đăng nhập, bắt đầu quá trình 2FA.
    """
    if request.method == "GET":
        return render_template("auth/login.html")
    
    # Xử lý POST request
    user = User() # Tạo instance của lớp User để gọi phương thức xử lý
    result, status_code = user.login(request.form)
    return jsonify(result), status_code

@auth.route("/signup", methods=["GET", "POST"])
def signup():
    """Endpoint xử lý yêu cầu đăng ký người dùng mới.
    GET: Hiển thị form đăng ký.
    POST: Xử lý yêu cầu đăng ký.
    """
    if request.method == "GET":
        return render_template("auth/signup.html")
    
    # Xử lý POST request
    user = User() # Tạo instance của lớp User để gọi phương thức xử lý
    result, status_code = user.signup(request.form)
    return jsonify(result), status_code

@auth.route("/logout") # Mặc định là GET
def signout():
    """Endpoint xử lý yêu cầu đăng xuất.
    Gọi phương thức signout của lớp User để xóa session.
    Trả về thông báo thành công dạng JSON.
    """
    user = User()
    result, status_code = user.signout()
    # Chuyển hướng về trang chủ sau khi đăng xuất
    return redirect("/")

@auth.route("/verify-2fa", methods=["POST"])
def verify_2fa():
    try:
        otp = request.form.get("otp")
        print(f"Received OTP: {otp}")
        if not otp:
            return jsonify({"error": "Thiếu mã OTP"}), 400

        user = User()
        result, status_code = user.verify_2fa(otp)
        print(f"Verify result: {result}, status: {status_code}")

        if "error" in result:
            return jsonify(result), 400
        elif "success" in result and result["success"] == True:
            return jsonify({"success": True, "redirect": "http://localhost:5000/"}), 200
        else:
            # Nếu bạn trả về user info thay vì có "success": True trong dict
            return jsonify({
                "success": True,
                "redirect": "http://localhost:5000/",
                "user": result  # gửi thêm user info nếu cần
            }), 200

    except Exception as e:
        print(f"Lỗi khi xác thực OTP: {e}", flush=True)
        return jsonify({"error": f"Lỗi xác thực: {str(e)}"}), 500


