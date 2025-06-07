# -*- coding: utf-8 -*-
import os
from datetime import timedelta # Di chuyển import lên đầu
from dotenv import load_dotenv

# Tải biến môi trường từ tệp .env (nếu có)
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

class Config:
    """Cấu hình cơ bản cho ứng dụng Flask."""
    # Khóa bí mật mạnh mẽ, LẤY TỪ BIẾN MÔI TRƯỜNG
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-should-really-change-this-secret-key"
    # URI kết nối MongoDB, LẤY TỪ BIẾN MÔI TRƯỜNG
    MONGO_URI = os.environ.get("MONGO_URI") or "mongodb://localhost:27017/MMH_DB_DEFAULT"
    # Thời gian hết hạn JWT (phút)
    JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", 15))
    # Thời gian sống của session (phút)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get("SESSION_LIFETIME_MINUTES", 30)))
    
    # Cấu hình Email cho 2FA (LẤY TỪ BIẾN MÔI TRƯỜNG)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "1", "t"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    
    # Đường dẫn lưu trữ tệp an toàn
    SECURE_STORAGE_PATH = os.environ.get("SECURE_STORAGE_PATH", os.path.join(basedir, "..", "secure_storage"))

    @staticmethod
    def init_app(app):
        # Tạo thư mục lưu trữ nếu chưa có
        os.makedirs(app.config["SECURE_STORAGE_PATH"], exist_ok=True)
        pass

class DevelopmentConfig(Config):
    """Cấu hình cho môi trường phát triển."""
    DEBUG = True
    MONGO_URI = os.environ.get("MONGO_URI_DEV") or "mongodb://localhost:27017/MMH_DB_DEV"

class TestingConfig(Config):
    """Cấu hình cho môi trường kiểm thử."""
    TESTING = True
    # Sử dụng DB riêng cho testing
    MONGO_URI = os.environ.get("MONGO_URI_TEST") or "mongodb://localhost:27017/MMH_DB_TEST"
    WTF_CSRF_ENABLED = False # Tắt CSRF protection trong form khi test
    MAIL_SUPPRESS_SEND = True # Không gửi email thật khi test
    # Đặt đường dẫn lưu trữ riêng cho test
    SECURE_STORAGE_PATH = os.environ.get("SECURE_STORAGE_PATH_TEST", os.path.join(basedir, "..", "secure_storage_test"))

class ProductionConfig(Config):
    """Cấu hình cho môi trường production."""
    # Đảm bảo SECRET_KEY và MONGO_URI được đặt trong biến môi trường cho production
    # DEBUG và TESTING phải là False
    DEBUG = False
    TESTING = False
    # Có thể thêm các cấu hình khác cho production (logging, etc.)

# Dictionary để map tên cấu hình với class tương ứng
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig # Cấu hình mặc định là development
}

# Xóa import timedelta ở cuối nếu còn sót

