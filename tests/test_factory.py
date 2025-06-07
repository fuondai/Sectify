# -*- coding: utf-8 -*-
from src import create_app

def test_config(test_config): # Sử dụng fixture test_config từ conftest
    """Kiểm tra xem app có được tạo với cấu hình testing không."""
    assert not create_app().testing # App mặc định không ở chế độ testing
    app = create_app(config_override=test_config) # Tạo app với config testing
    assert app.testing
    assert app.config["SECRET_KEY"] == "test-secret-key-please-change"
    assert "MMH_DB_TEST" in app.config["MONGO_URI"]

def test_hello(client): # Sử dụng fixture client từ conftest
    """Kiểm tra route cơ bản (ví dụ: trang chủ hoặc route chào mừng)."""
    # Giả định có một route đơn giản tại "/" hoặc "/api/ping"
    # Cần tạo route này trong __init__.py hoặc một blueprint đơn giản
    # Tạm thời giả định route "/" trả về status 200
    # response = client.get("/")
    # assert response.status_code == 200 
    # assert b"Welcome" in response.data # Kiểm tra nội dung nếu có
    
    # Hoặc kiểm tra một endpoint API đơn giản nếu có
    # response = client.get("/api/ping")
    # assert response.status_code == 200
    # assert response.json == {"message": "pong"}
    pass # Sẽ thêm test cụ thể khi có route cơ bản

