# -*- coding: utf-8 -*-
import sys
import io

# Cấu hình lại stdout để hỗ trợ UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from flask import jsonify, session, redirect, current_app, request # Import request để lấy dữ liệu form
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pymongo import MongoClient
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
from datetime import datetime, timedelta, timezone # Import timezone để làm việc với thời gian UTC
import jwt
import os
from bson import ObjectId

# --- Khởi tạo các đối tượng cần thiết --- 
ph = PasswordHasher() # Đối tượng để băm và xác thực mật khẩu bằng Argon2

# --- Kết nối DB --- 
def get_db():
    """Lấy đối tượng database MongoDB từ application context.
    Sử dụng application context để quản lý kết nối DB trong một request.
    """
    # Kiểm tra xem kết nối đã tồn tại trong context chưa
    if not hasattr(current_app, "db_client") or not hasattr(current_app, "db"):
        mongo_uri = current_app.config.get("MONGO_URI") # Lấy URI từ config
        if not mongo_uri:
            raise ValueError("MONGO_URI chưa được cấu hình trong ứng dụng.")
        try:
            # Kết nối tới MongoDB, đặt timeout để xử lý lỗi kết nối nhanh hơn
            current_app.db_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            current_app.db_client.admin.command("ismaster") # Kiểm tra kết nối thành công
            db_name = current_app.db_client.get_database().name # Lấy tên DB từ URI
            current_app.db = current_app.db_client[db_name] # Lưu đối tượng DB vào context
            print(f"Đã kết nối thành công tới MongoDB: {db_name} qua get_db()")
        except Exception as e:
            print(f"Kết nối tới MongoDB thất bại qua get_db(): {e}")
            raise ConnectionError(f"Không thể kết nối tới MongoDB: {e}")
    return current_app.db # Trả về đối tượng DB

class User:
    """Lớp chứa các phương thức xử lý logic liên quan đến người dùng:
    đăng ký, đăng nhập, đăng xuất, quản lý session, 2FA.
    """
    def __init__(self):
        # Hiện tại không cần khởi tạo gì đặc biệt
        pass

    def generatetoken(self, userid):
        """Tạo JWT token cho người dùng sau khi đăng nhập thành công.
        Token chứa ID người dùng và thời gian hết hạn.
        """
        secret_key = current_app.config.get("SECRET_KEY") # Lấy khóa bí mật từ config
        if not secret_key:
            print("Lỗi: SECRET_KEY chưa được cấu hình.")
            return None
        try:
            payload = {
                "id": userid, # ID của người dùng
                # Sử dụng thời gian UTC để đảm bảo tính nhất quán
                "exp": datetime.now(timezone.utc) + timedelta(minutes=current_app.config.get("JWT_EXPIRATION_MINUTES", 15))
            }
            # Tạo token bằng HS256
            token = jwt.encode(payload=payload, key=secret_key, algorithm="HS256")
            return token
        except Exception as e:
            print(f"Lỗi tạo JWT token: {e}")
            return None

    def start_session(self, user):
        """Bắt đầu một session mới cho người dùng sau khi xác thực thành công (bao gồm cả 2FA).
        Lưu thông tin cần thiết vào session và tạo JWT token.
        """
        # Xóa mật khẩu khỏi đối tượng user trước khi lưu vào session hoặc trả về
        if "password" in user:
            del user["password"]
        session.permanent = True # Đặt session là permanent (dựa vào config PERMANENT_SESSION_LIFETIME)
        session["logged_in"] = True
        session["user_id"] = user["_id"]
        session["role"] = user.get("role", "user") # Lấy role, mặc định là "user"
        
        # Tạo JWT token
        token = self.generatetoken(user["_id"])
        if not token:
             # Trả về lỗi nếu không tạo được token
             return {"error": "Không thể tạo token phiên làm việc"}, 500
        session["token"] = token
        
        # Xóa các thông tin tạm thời của 2FA khỏi session
        session.pop("temp_user_id_for_2fa", None)
        session.pop("2fa_otp", None)
        session.pop("2fa_otp_timestamp", None)
        print(f"Session đã bắt đầu cho người dùng: {user.get('email')}")
        
        # Chuẩn bị thông tin người dùng để trả về cho client (không bao gồm dữ liệu nhạy cảm)
        user_info_for_client = {
            "_id": user["_id"],
            "name": user.get("name"),
            "email": user.get("email"),
            "role": user.get("role", "user"),
            "token": token # Trả token về cho client lưu trữ (ví dụ: localStorage)
        }
        # Trả về thông tin người dùng và mã trạng thái thành công
        return user_info_for_client, 200

    def signup(self, form_data):
        """Xử lý yêu cầu đăng ký người dùng mới.
        Kiểm tra dữ liệu đầu vào, hash mật khẩu, kiểm tra email tồn tại, lưu vào DB.
        """
        print(f"Yêu cầu đăng ký với dữ liệu: {form_data}")
        db = get_db() # Lấy đối tượng DB
        name = form_data.get("name")
        email = form_data.get("email")
        password = form_data.get("password")

        # Kiểm tra các trường bắt buộc
        if not all([name, email, password]):
            return {"error": "Thiếu các trường bắt buộc (name, email, password)"}, 400
        # Kiểm tra độ dài mật khẩu
        if len(password) < 8:
             return {"error": "Mật khẩu phải có ít nhất 8 ký tự"}, 400

        # Tạo đối tượng người dùng mới
        user = {
            "_id": uuid.uuid4().hex, # Tạo ID duy nhất
            "name": name,
            "email": email.lower(), # Lưu email dạng chữ thường để tránh trùng lặp
            "role": "user", # Mặc định role là user
            "created_at": datetime.now(timezone.utc) # Lưu thời gian tạo (UTC)
        }

        try:
            # Băm mật khẩu bằng Argon2
            user["password"] = ph.hash(password)
            print(f"Đã băm mật khẩu thành công cho {email}")
        except Exception as e:
            print(f"Lỗi băm mật khẩu cho {email}: {e}")
            return {"error": "Không thể bảo mật mật khẩu"}, 500

        # Kiểm tra xem email đã tồn tại trong DB chưa
        if db.users.find_one({"email": user["email"]}):
            print(f"Đăng ký thất bại: Email {email} đã được sử dụng.")
            # Trả về lỗi trùng email (thông báo tiếng Việt theo yêu cầu test)
            return {"error": "Địa chỉ email đã được sử dụng"}, 400

        try:
            # Thêm người dùng mới vào collection 'users'
            if db.users.insert_one(user):
                print(f"Người dùng {email} đã đăng ký thành công.")
                # Trả về thông báo thành công (tiếng Việt theo yêu cầu test)
                return {"message": "Đăng ký thành công. Vui lòng đăng nhập."}, 201
            else:
                print(f"Đăng ký thất bại: Lỗi ghi DB cho {email}.")
                return {"error": "Đăng ký thất bại do lỗi cơ sở dữ liệu"}, 500
        except Exception as e:
             print(f"Đăng ký thất bại: Ngoại lệ khi ghi DB cho {email}: {e}")
             return {"error": "Lỗi không mong muốn trong quá trình đăng ký"}, 500

    def signout(self):
        """Xử lý yêu cầu đăng xuất.
        Xóa toàn bộ dữ liệu trong session của người dùng.
        """
        user_id = session.get("user_id", "Người dùng không xác định")
        session.clear() # Xóa session
        print(f"Người dùng {user_id} đã đăng xuất.")
        # Trả về thông báo thành công (tiếng Việt theo yêu cầu test)
        return {"message": "Đăng xuất thành công"}, 200

    def login(self, form_data):
        """Xử lý yêu cầu đăng nhập.
        Kiểm tra email, xác thực mật khẩu, chuẩn bị và yêu cầu 2FA.
        """
        db = get_db() # Lấy đối tượng DB
        email = form_data.get("email")
        password = form_data.get("password")

        # Kiểm tra email và password có được cung cấp không
        if not email or not password:
             return {"error": "Yêu cầu email và mật khẩu"}, 400

        print(f"Nỗ lực đăng nhập cho email: {email}")
        # Tìm người dùng bằng email (chữ thường)
        user = db.users.find_one({"email": email.lower()})

        # Nếu không tìm thấy người dùng
        if not user:
            print(f"Đăng nhập thất bại: Không tìm thấy người dùng {email}")
            # Trả về lỗi (thông báo tiếng Việt theo yêu cầu test)
            return {"error": "Thông tin đăng nhập không hợp lệ"}, 401

        try:
            # Lấy mật khẩu đã hash từ DB
            hashed_password = user.get("password")
            if not hashed_password:
                 print(f"Đăng nhập thất bại: Người dùng {email} không có hash mật khẩu.")
                 return {"error": "Lỗi xác thực"}, 500

            # Xác thực mật khẩu người dùng nhập với hash trong DB
            ph.verify(hashed_password, password)
            print(f"Xác thực mật khẩu thành công cho {email}")

            # Kiểm tra xem hash có cần được cập nhật không (ví dụ: tham số Argon2 thay đổi)
            if ph.check_needs_rehash(hashed_password):
                print(f"Cần rehash mật khẩu cho {email}")
                new_hash = ph.hash(password)
                db.users.update_one({"_id": user["_id"]}, {"$set": {"password": new_hash}})

            # Lưu tạm user_id vào session để chờ xác thực 2FA
            session["temp_user_id_for_2fa"] = str(user["_id"])
            print(f"[DEBUG] Đã lưu temp_user_id_for_2fa vào session: {session['temp_user_id_for_2fa']}")
            
            # Gửi mã 2FA (hoặc bỏ qua nếu đang testing)
            mail_sent = self.send_2fa_code(user["email"], current_app.config.get("TESTING", False))
            
            # In ra toàn bộ session để debug
            print(f"[DEBUG] Session sau khi lưu 2FA: {dict(session)}")
            
            if mail_sent:
                print(f"Đã gửi/bỏ qua mã 2FA cho {email}. Yêu cầu xác thực 2FA.")
                # Trả về thông báo yêu cầu 2FA (tiếng Việt theo yêu cầu test)
                return {"message": "Yêu cầu xác thực hai yếu tố", "requires_2fa": True}, 200
            else:
                print(f"Đăng nhập thất bại: Không thể gửi/bỏ qua mã 2FA cho {email}")
                return {"error": "Không thể gửi mã xác thực"}, 500

        except VerifyMismatchError:
            # Sai mật khẩu
            print(f"Đăng nhập thất bại: Sai mật khẩu cho {email}")
            # Trả về lỗi (thông báo tiếng Việt theo yêu cầu test)
            return {"error": "Thông tin đăng nhập không hợp lệ"}, 401
        except Exception as e:
            # Các lỗi không mong muốn khác
            print(f"Đăng nhập thất bại: Lỗi không mong muốn cho {email}: {e}")
            return {"error": "Lỗi không mong muốn trong quá trình đăng nhập"}, 500

    def send_2fa_code(self, email, testing=False):
        """Tạo mã OTP 6 số, lưu vào session và gửi qua email.
        Bỏ qua việc gửi email thực tế nếu `testing` là True hoặc config MAIL_SUPPRESS_SEND=True.
        """
        # Tạo mã OTP ngẫu nhiên 6 chữ số
        otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
        session["2fa_otp"] = otp # Lưu OTP vào session
        # Lưu timestamp (UTC) để kiểm tra hết hạn
        otp_timestamp = datetime.now(timezone.utc)
        session["2fa_otp_timestamp"] = otp_timestamp
        
        # Debug: In ra thông tin session sau khi lưu OTP
        print(f"[DEBUG] Đã lưu OTP vào session - 2fa_otp: {session['2fa_otp']}")
        print(f"[DEBUG] Đã lưu timestamp vào session - 2fa_otp_timestamp: {session['2fa_otp_timestamp']}")
        
        # Ghi log thông tin OTP
        current_app.logger.info(f"Mã OTP được tạo cho {email}: {otp}")
        current_app.logger.info(f"Thời gian tạo OTP (UTC): {otp_timestamp.isoformat()}")
        current_app.logger.info(f"OTP sẽ hết hạn vào (UTC): {(otp_timestamp + timedelta(minutes=10)).isoformat()}")

        # Bỏ qua gửi email thực tế khi đang chạy test, development, hoặc có config yêu cầu
        if testing or current_app.config.get("MAIL_SUPPRESS_SEND") or current_app.config.get("DEBUG", False):
            print(f"DEBUG/TESTING/MAIL_SUPPRESS_SEND=True: Bỏ qua gửi email thực tế cho {email}. OTP: {otp}")
            return True # Giả lập gửi thành công

        # Lấy thông tin cấu hình email từ biến môi trường
        sender_email = os.environ.get("MAIL_USERNAME")
        sender_password = os.environ.get("MAIL_PASSWORD")
        smtp_server_host = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
        smtp_server_port = int(os.environ.get("MAIL_PORT", 587))

        # Kiểm tra cấu hình email
        if not sender_email or not sender_password:
            print("Lỗi gửi mail 2FA: MAIL_USERNAME hoặc MAIL_PASSWORD chưa được cấu hình.")
            return False

        # Tạo nội dung email
        msg = MIMEMultipart()
        msg["Subject"] = "Mã Xác Thực Hai Yếu Tố Của Bạn"
        msg["From"] = sender_email
        msg["To"] = email
        body = f"Mã xác thực hai yếu tố của bạn là: {otp}\nMã này sẽ hết hạn sau 5 phút."
        msg.attach(MIMEText(body, "plain"))

        try:
            # Kết nối và gửi email qua SMTP
            print(f"Đang cố gắng gửi mã 2FA tới {email} qua {smtp_server_host}:{smtp_server_port}")
            with smtplib.SMTP(smtp_server_host, smtp_server_port) as smtp_server:
                smtp_server.starttls() # Bật TLS
                smtp_server.login(sender_email, sender_password) # Đăng nhập
                smtp_server.send_message(msg) # Gửi mail
            print(f"Đã gửi email 2FA thành công tới {email}")
            return True
        except smtplib.SMTPAuthenticationError:
             # Lỗi xác thực SMTP
             print(f"Lỗi gửi mail 2FA: Xác thực SMTP thất bại cho {sender_email}.")
             return False
        except Exception as e:
            # Các lỗi khác (kết nối, timeout, ...)
            print(f"Lỗi gửi mail 2FA tới {email}: {str(e)}")
            return False

    def verify_2fa(self, otp):
        """Xác thực mã OTP 2FA do người dùng nhập.
        Kiểm tra OTP, thời gian hết hạn, và bắt đầu session nếu hợp lệ.
        """
        db = get_db() # Lấy đối tượng DB
        
        # Debug: In ra toàn bộ session hiện tại
        print(f"[DEBUG] Session data before getting values: {dict(session)}")
        print(f"[DEBUG] Session ID: {session.sid if hasattr(session, 'sid') else 'No session ID'}")
        print(f"[DEBUG] Session permanent: {session.permanent}")
        print(f"[DEBUG] Session modified: {session.modified}")
        
        # Lấy thông tin cần thiết từ session
        temp_user_id = session.get("temp_user_id_for_2fa")
        stored_otp = session.get("2fa_otp")
        otp_timestamp_aware = session.get("2fa_otp_timestamp")
        
        # Debug: In ra các giá trị đã lấy từ session
        print(f"[DEBUG] Retrieved from session - temp_user_id: {temp_user_id}")
        print(f"[DEBUG] Retrieved from session - stored_otp: {stored_otp}")
        print(f"[DEBUG] Retrieved from session - otp_timestamp_aware: {otp_timestamp_aware}")
        print(f"[DEBUG] Submitted OTP: {otp}")
        
        # Kiểm tra xem session có chứa các giá trị cần thiết không
        if not all([temp_user_id, stored_otp, otp_timestamp_aware]):
            print("[ERROR] Missing required session data for 2FA verification")
            print(f"[ERROR] temp_user_id: {'exists' if temp_user_id else 'missing'}")
            print(f"[ERROR] stored_otp: {'exists' if stored_otp else 'missing'}")
            print(f"[ERROR] otp_timestamp_aware: {'exists' if otp_timestamp_aware else 'missing'}")
            return {"error": "Thông tin xác thực không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại."}
        
        # Chuyển đổi timestamp từ str thành datetime nếu cần
        if isinstance(otp_timestamp_aware, str):
            otp_timestamp_aware = datetime.strptime(
                otp_timestamp_aware, "%Y-%m-%d %H:%M:%S.%f%z"
            )

        # Kiểm tra thời gian hết hạn (10 phút = 600 giây)
        now = datetime.now(timezone.utc)
        time_diff = now - otp_timestamp_aware
        
        if time_diff.total_seconds() > 600:
            # Xóa thông tin tạm thời nếu hết hạn
            session.pop("temp_user_id_for_2fa", None)
            session.pop("2fa_otp", None)
            session.pop("2fa_otp_timestamp", None)
            print(f"[ERROR] OTP expired: {time_diff.total_seconds()} seconds")
            return {"error": "Mã OTP đã hết hạn. Vui lòng đăng nhập lại."}

        # Chuyển đổi cả hai về chuỗi để so sánh
        stored_otp_str = str(stored_otp).strip()
        submitted_otp_str = str(otp).strip()
        
        print(f"[DEBUG] Comparing OTPs - stored: '{stored_otp_str}', submitted: '{submitted_otp_str}'")
        
        # Kiểm tra OTP có trùng khớp không
        if submitted_otp_str != stored_otp_str:
            print(f"[ERROR] OTP mismatch: stored='{stored_otp_str}', submitted='{submitted_otp_str}'")
            return {"error": "Mã OTP không chính xác."}

        # OTP hợp lệ, xác thực thành công!
        try:
            # Lấy thông tin người dùng từ database
            user = db.users.find_one({"_id": temp_user_id})
            if not user:
                return {"error": "Không tìm thấy thông tin người dùng."}

            # Xóa thông tin tạm thời sau khi xác thực thành công
            session.pop("temp_user_id_for_2fa", None)
            session.pop("2fa_otp", None)
            session.pop("2fa_otp_timestamp", None)
            
            # Lưu lại session
            session.modified = True
            
            # Bắt đầu session mới cho người dùng
            return self.start_session(user)

        except Exception as e:
            print(f"[ERROR] Error in 2FA verification: {str(e)}")
            return {"error": f"Lỗi xác thực: {str(e)}"}