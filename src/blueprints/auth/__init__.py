# -*- coding: utf-8 -*-
from flask import Blueprint

# Tạo blueprint instance
auth = Blueprint("auth", __name__, template_folder="templates", static_folder="static")

# Import các routes của blueprint này
# Phải import sau khi tạo blueprint instance để tránh circular imports
from . import routes, models # Đảm bảo routes.py và models.py tồn tại và có nội dung cần thiết

