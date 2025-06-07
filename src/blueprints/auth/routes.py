# -*- coding: utf-8 -*-
from flask import request, session, redirect, render_template, jsonify, current_app
from . import auth # Import blueprint instance từ __init__.py cùng cấp
from .models import User # Import lớp User từ models.py cùng cấp

# Sử dụng decorator của blueprint (@auth.route) thay vì @app.route
# để đăng ký các route này với blueprint 'auth'

@auth.route("/signup", methods=["POST"])
def signup():
    """Endpoint xử lý yêu cầu đăng ký người dùng mới.
    Chỉ chấp nhận phương thức POST.
    Lấy dữ liệu từ form, gọi phương thức signup của lớp User.
    Trả về kết quả dạng JSON.
    """
    user = User() # Tạo instance của lớp User để gọi phương thức xử lý
    # Gọi phương thức signup từ model, truyền dữ liệu form (request.form)
    result, status_code = user.signup(request.form)
    # Trả về kết quả (thành công hoặc lỗi) và mã trạng thái HTTP dưới dạng JSON
    return jsonify(result), status_code

@auth.route("/logout") # Mặc định là GET
def signout():
    """Endpoint xử lý yêu cầu đăng xuất.
    Gọi phương thức signout của lớp User để xóa session.
    Trả về thông báo thành công dạng JSON.
    """
    user = User()
    result, status_code = user.signout()
    # Thông thường, đăng xuất có thể redirect về trang đăng nhập hoặc trang chủ.
    # Ở đây, trả về JSON theo logic của model.
    return jsonify(result), status_code

@auth.route("/login", methods=["POST"])
def login():
    """Endpoint xử lý yêu cầu đăng nhập.
    Chỉ chấp nhận phương thức POST.
    Lấy dữ liệu từ form, gọi phương thức login của lớp User (bắt đầu quá trình 2FA).
    Trả về kết quả dạng JSON (yêu cầu 2FA hoặc lỗi).
    """
    user = User()
    result, status_code = user.login(request.form)
    return jsonify(result), status_code

@auth.route("/verify-2fa", methods=["POST"])
def verify_2fa():
    """Endpoint xử lý xác thực mã OTP 2FA.
    Chỉ chấp nhận phương thức POST.
    Lấy mã OTP từ form, gọi phương thức verify_2fa của lớp User.
    Trả về kết quả dạng JSON (thông tin user nếu thành công, hoặc lỗi).
    """
    user = User()
    # Chỉ xử lý POST request chứa mã OTP
    if request.method == "POST":
        otp = request.form.get("otp") # Lấy mã OTP từ form
        if not otp:
            return jsonify({"error": "Missing OTP code in form data"}), 400
        result, status_code = user.verify_2fa(otp)
        return jsonify(result), status_code
    # else: # Không xử lý GET request cho API này
    #     # Nếu là ứng dụng web truyền thống, có thể trả về template:
    #     # return render_template("verify_2fa.html")
    #     # Đối với API, trả về lỗi Method Not Allowed nếu không phải POST
    #     return jsonify({"error": "Method Not Allowed. Use POST to submit OTP."}), 405

