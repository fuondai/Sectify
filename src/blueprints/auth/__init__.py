# -*- coding: utf-8 -*-
import sys
import io

# Cấu hình lại stdout để hỗ trợ UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from flask import Blueprint

# Tạo blueprint instance
auth = Blueprint("auth", __name__, template_folder="templates", static_folder="static")

# Import các routes của blueprint này
# Phải import sau khi tạo blueprint instance để tránh circular imports
from . import routes, models # Đảm bảo routes.py và models.py tồn tại và có nội dung cần thiết

