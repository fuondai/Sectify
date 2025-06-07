# -*- coding: utf-8 -*-
import pytest
from flask import session, url_for

# --- Test Authentication Blueprint --- 

def test_signup(client): # Sử dụng fixture client từ conftest
    """Kiểm tra chức năng đăng ký."""
    response = client.post("/auth/signup", data={
        "name": "New User",
        "email": "newuser@example.com",
        "password": "password123"
    })
    assert response.status_code == 201 # Created
    assert response.json["message"] == "Đăng ký thành công. Vui lòng đăng nhập."
    
    # Kiểm tra xem user có trong DB không (cần truy cập DB trong test, có thể cần fixture riêng)
    # from pymongo import MongoClient
    # client_db = MongoClient(os.environ["MONGO_URI_TEST"])
    # db = client_db.get_database()
    # assert db.users.find_one({"email": "newuser@example.com"})
    # client_db.close()

def test_signup_duplicate_email(client):
    """Kiểm tra đăng ký với email đã tồn tại."""
    # Đăng ký lần đầu
    client.post("/auth/signup", data={
        "name": "Existing User",
        "email": "existing@example.com",
        "password": "password123"
    })
    # Đăng ký lần hai với cùng email
    response = client.post("/auth/signup", data={
        "name": "Another User",
        "email": "existing@example.com",
        "password": "anotherpassword"
    })
    assert response.status_code == 400
    assert "Địa chỉ email đã được sử dụng" in response.json["error"]

def test_login_requires_2fa(client):
    """Kiểm tra đăng nhập thành công và yêu cầu 2FA."""
    # Đăng ký trước
    client.post("/auth/signup", data={
        "name": "Login User",
        "email": "login@example.com",
        "password": "password123"
    })
    # Đăng nhập
    response = client.post("/auth/login", data={
        "email": "login@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert response.json["requires_2fa"] == True
    assert "message" in response.json
    # Kiểm tra xem user_id tạm thời có trong session không
    with client.session_transaction() as sess:
        assert "temp_user_id_for_2fa" in sess
        assert "2fa_otp" in sess

def test_login_invalid_password(client):
    """Kiểm tra đăng nhập với mật khẩu sai."""
    client.post("/auth/signup", data={
        "name": "WrongPass User",
        "email": "wrongpass@example.com",
        "password": "correctpassword"
    })
    response = client.post("/auth/login", data={
        "email": "wrongpass@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Thông tin đăng nhập không hợp lệ" in response.json["error"]

def test_login_user_not_found(client):
    """Kiểm tra đăng nhập với email không tồn tại."""
    response = client.post("/auth/login", data={
        "email": "nosuchuser@example.com",
        "password": "anypassword"
    })
    assert response.status_code == 401
    assert "Thông tin đăng nhập không hợp lệ" in response.json["error"]

def test_verify_2fa_correct(client):
    """Kiểm tra xác thực 2FA thành công."""
    # Đăng ký và đăng nhập để lấy OTP
    client.post("/auth/signup", data={"name": "2FA User", "email": "2fa_correct@example.com", "password": "password123"})
    client.post("/auth/login", data={"email": "2fa_correct@example.com", "password": "password123"})
    
    # Lấy OTP từ session
    with client.session_transaction() as sess:
        otp = sess["2fa_otp"]
        temp_user_id = sess["temp_user_id_for_2fa"]
        
    # Xác thực với OTP đúng
    response = client.post("/auth/verify-2fa", data={"otp": otp})
    assert response.status_code == 200
    assert "token" in response.json
    # Kiểm tra session đã được thiết lập đúng chưa
    with client.session_transaction() as sess:
        assert sess["logged_in"] == True
        assert sess["user_id"] == temp_user_id
        assert "token" in sess
        # Dữ liệu tạm thời phải bị xóa
        assert "temp_user_id_for_2fa" not in sess
        assert "2fa_otp" not in sess

def test_verify_2fa_incorrect(client):
    """Kiểm tra xác thực 2FA với OTP sai."""
    client.post("/auth/signup", data={"name": "2FA Incorrect", "email": "2fa_incorrect@example.com", "password": "password123"})
    client.post("/auth/login", data={"email": "2fa_incorrect@example.com", "password": "password123"})
    
    # Xác thực với OTP sai
    response = client.post("/auth/verify-2fa", data={"otp": "000000"})
    assert response.status_code == 401
    assert "Mã xác thực hai yếu tố không hợp lệ" in response.json["error"]
    # Kiểm tra session chưa được thiết lập
    with client.session_transaction() as sess:
        assert not sess.get("logged_in")
        assert "user_id" not in sess
        # Dữ liệu tạm thời vẫn còn
        assert "temp_user_id_for_2fa" in sess 

def test_logout(logged_in_client): # Sử dụng fixture client đã đăng nhập
    """Kiểm tra chức năng đăng xuất."""
    # Kiểm tra trạng thái đăng nhập trước khi logout
    with logged_in_client.session_transaction() as sess:
        assert sess.get("logged_in") == True
        assert "user_id" in sess
        assert "token" in sess
        
    response = logged_in_client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200 # Sau redirect về trang login
    # Kiểm tra xem session đã bị xóa chưa
    with logged_in_client.session_transaction() as sess:
        assert not sess.get("logged_in")
        assert "user_id" not in sess
        assert "token" not in sess

# Thêm các test case khác: 
# - Test 2FA hết hạn
# - Test truy cập trang yêu cầu đăng nhập khi chưa đăng nhập
# - Test truy cập trang yêu cầu token khi token không hợp lệ/hết hạn
# - Test các trường hợp lỗi khác (thiếu input, etc.)

