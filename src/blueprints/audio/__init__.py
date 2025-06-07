# -*- coding: utf-8 -*-
from flask import Blueprint

# Tạo blueprint instance cho audio
audio = Blueprint("audio", __name__, template_folder="templates", static_folder="static")

# Import các routes của blueprint này
# Phải import sau khi tạo blueprint instance
from . import routes # Đảm bảo routes.py tồn tại trong cùng thư mục

