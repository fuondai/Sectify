# -*- coding: utf-8 -*-
import os
from flask import Flask
from pymongo import MongoClient
from config import config # Import cấu hình từ config.py
import sys

# Biến toàn cục cho client MongoDB (sẽ được khởi tạo trong create_app)
# Hoặc sử dụng extension như Flask-PyMongo để quản lý tốt hơn
db = None

# Lớp giả lập MongoDB cho môi trường phát triển
class MockMongoCollection:
    def __init__(self):
        self.data = []
        
    def insert_one(self, document):
        self.data.append(document)
        return type('obj', (object,), {'inserted_id': id(document)})
        
    def find_one(self, query):
        for doc in self.data:
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                return doc
        return None
        
    def find(self, query=None):
        if query is None:
            return self.data
        results = []
        for doc in self.data:
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                results.append(doc)
        return results
        
    def update_one(self, query, update, upsert=False):
        doc = self.find_one(query)
        if doc:
            if "$set" in update:
                for key, value in update["$set"].items():
                    doc[key] = value
            return type('obj', (object,), {'modified_count': 1})
        elif upsert:
            new_doc = {}
            for key, value in query.items():
                new_doc[key] = value
            if "$set" in update:
                for key, value in update["$set"].items():
                    new_doc[key] = value
            self.data.append(new_doc)
            return type('obj', (object,), {'modified_count': 0, 'upserted_id': id(new_doc)})
        return type('obj', (object,), {'modified_count': 0})
        
    def delete_one(self, query):
        for i, doc in enumerate(self.data):
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                del self.data[i]
                return type('obj', (object,), {'deleted_count': 1})
        return type('obj', (object,), {'deleted_count': 0})

class MockMongoDB:
    def __init__(self):
        self.collections = {}
        
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockMongoCollection()
        return self.collections[name]

def create_app(config_name="default", config_override=None):
    """Application Factory: Tạo và cấu hình instance Flask app.

    Args:
        config_name (str): Tên của cấu hình để sử dụng (ví dụ: "development", "testing", "production").
        config_override (dict, optional): Dictionary để ghi đè các giá trị cấu hình cụ thể.

    Returns:
        Flask: Instance của Flask application đã được cấu hình.
    """
    global db # Sử dụng biến db toàn cục

    app = Flask(__name__, instance_relative_config=False) # Tạo instance Flask

    # --- Tải Cấu hình --- 
    # Lấy class cấu hình từ dictionary `config` dựa trên `config_name`
    cfg = config.get(config_name, config["default"])
    app.config.from_object(cfg) # Tải cấu hình từ object
    
    # Ghi đè cấu hình nếu có (hữu ích cho testing)
    if config_override:
        app.config.update(config_override)
        
    # Kiểm tra SECRET_KEY (rất quan trọng)
    if not app.config.get("SECRET_KEY"):
        raise ValueError("SECRET_KEY is not set in the configuration!")
        
    # Gọi hàm init_app của config (nếu có)
    if hasattr(cfg, "init_app"):
        cfg.init_app(app)

    # --- Khởi tạo Kết nối Database --- 
    # Sử dụng pymongo trực tiếp (như trong models hiện tại)
    # Lưu ý: Quản lý kết nối DB tốt hơn nên dùng Flask-PyMongo
    mongo_uri = app.config.get("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI is not set in the configuration!")
    try:
        client = MongoClient(mongo_uri)
        # Kiểm tra kết nối
        client.admin.command("ismaster") 
        # Lấy database từ URI hoặc tên mặc định (cần chuẩn hóa cách lấy tên DB)
        # Ví dụ: lấy tên DB từ URI nếu có, nếu không thì dùng tên mặc định
        db_name = MongoClient(mongo_uri).get_database().name
        db = client[db_name] # Gán vào biến db toàn cục
        print(f"Successfully connected to MongoDB database: {db_name}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        if config_name == "development" or config_name == "testing":
            print("Using mock in-memory database for development/testing")
            db = MockMongoDB()
        else:
            db = None # Đặt là None nếu kết nối lỗi
            # Dừng ứng dụng nếu không thể kết nối DB ở môi trường production
            if config_name == "production":
                print("Cannot start application in production without MongoDB")
                sys.exit(1)

    # --- Đăng ký Blueprints --- 
    # Import blueprints bên trong factory để tránh circular imports
    from .blueprints.auth import auth as auth_blueprint
    from .blueprints.audio import audio as audio_blueprint
    # Thêm các blueprint khác nếu có
    
    app.register_blueprint(auth_blueprint, url_prefix="/auth")
    app.register_blueprint(audio_blueprint, url_prefix="/audio")
    # Đăng ký các blueprint khác...

    # --- Cấu hình khác (Logging, Extensions, etc.) --- 
    # Ví dụ: Cấu hình logging
    # if not app.debug and not app.testing:
    #     # ... setup logging for production ...
    #     pass

    # --- Route cơ bản (tùy chọn) --- 
    @app.route("/ping")
    def ping():
        return "pong"
        
    @app.route("/")
    def index():
        return "Chào mừng đến với ứng dụng Mã hóa Âm thanh An toàn"

    print(f"Flask app created with config: {config_name}")
    return app

