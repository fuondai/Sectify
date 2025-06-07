#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from src import create_app

# Tạo ứng dụng Flask sử dụng cấu hình từ biến môi trường
config_name = os.environ.get("FLASK_CONFIG", "development")
app = create_app(config_name)

if __name__ == "__main__":
    # Chạy ứng dụng với chế độ debug nếu không phải là production
    debug = config_name != "production"
    app.run(debug=debug)
