# -*- coding: utf-8 -*-
import pytest
import os
from src import create_app # Import application factory
import shutil # For directory cleanup

# --- Fixtures --- 

@pytest.fixture(scope='module') # Sửa lỗi cú pháp: dùng 'module' thay vì \'module\'
def test_config():
    """Cấu hình riêng cho môi trường test."""
    os.environ["FLASK_ENV"] = "testing"
    os.environ["MONGO_URI"] = os.environ.get("MONGO_URI_TEST", "mongodb://localhost:27017/MMH_DB_TEST")
    os.environ["SECRET_KEY"] = "test-secret-key-please-change"
    os.environ["MAIL_USERNAME"] = "test@example.com"
    os.environ["MAIL_PASSWORD"] = "testpassword"
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    test_storage_path = os.environ.get("SECURE_STORAGE_PATH_TEST", os.path.join(basedir, "..", "secure_storage_test"))
    os.makedirs(test_storage_path, exist_ok=True)
    
    config = {
        "TESTING": True,
        "SECRET_KEY": os.environ["SECRET_KEY"],
        "MONGO_URI": os.environ["MONGO_URI"],
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True,
        "SECURE_STORAGE_PATH": test_storage_path
    }
    yield config
    
    print("\n--- Cleaning up test database ---")
    try:
        from pymongo import MongoClient
        client = MongoClient(config["MONGO_URI"])
        db_name = client.get_database().name
        client.drop_database(db_name)
        print(f"Dropped test database: {db_name}")
    except Exception as e:
        print(f"Error dropping test database: {e}")
        
    print("--- Cleaning up test storage directory ---")
    storage_path_to_clean = config["SECURE_STORAGE_PATH"]
    if os.path.exists(storage_path_to_clean):
        try:
            shutil.rmtree(storage_path_to_clean)
            print(f"Removed test storage directory: {storage_path_to_clean}")
        except Exception as e:
            print(f"Error removing test storage directory {storage_path_to_clean}: {e}")
    else:
        print(f"Test storage directory not found for cleanup: {storage_path_to_clean}")

@pytest.fixture(scope='module') # Sửa lỗi cú pháp
def app(test_config):
    """Tạo instance của Flask app cho test."""
    _app = create_app(config_name="testing", config_override=test_config)
    ctx = _app.app_context()
    ctx.push()
    yield _app
    ctx.pop()

@pytest.fixture(scope='module') # Sửa lỗi cú pháp
def client(app):
    """Tạo test client cho Flask app."""
    return app.test_client()

@pytest.fixture(scope='function') # Sửa lỗi cú pháp: dùng 'function'
def logged_in_client(client):
    """Tạo test client đã đăng nhập (sau khi đăng ký và xác thực 2FA thành công)."""
    signup_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    }
    signup_url = "/auth/signup"
    login_url = "/auth/login"
    verify_url = "/auth/verify-2fa"
        
    signup_response = client.post(signup_url, data=signup_data)
    if signup_response.status_code != 201:
         if signup_response.status_code == 400 and b"Email address already in use" in signup_response.data:
             print("Signup skipped: User already exists (likely from previous test in module).")
         else:
             pytest.fail(f"Signup step failed. Status: {signup_response.status_code}, Response: {signup_response.data}")

    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post(login_url, data=login_data) 
    if response.status_code != 200 or not response.is_json or response.json.get("requires_2fa") != True:
         pytest.fail(f"Login step failed or did not require 2FA. Status: {response.status_code}, Response: {response.data}")
    
    with client.session_transaction() as sess:
        if "2fa_otp" not in sess:
             pytest.fail("2FA OTP not found in session after login step.")
        otp = sess["2fa_otp"]
        
    verify_data = {"otp": otp}
    response = client.post(verify_url, data=verify_data) 
    if response.status_code != 200 or not response.is_json or "token" not in response.json:
         pytest.fail(f"2FA verification step failed. Status: {response.status_code}, Response: {response.data}")
    
    print("\nClient logged in successfully for test function.")
    return client

