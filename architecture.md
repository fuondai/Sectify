# Kiến trúc Hệ thống - Ứng dụng Mã hóa Âm thanh

## Tổng quan

Ứng dụng được xây dựng theo kiến trúc Monolithic với các module được phân tách rõ ràng bằng Flask Blueprints. Kiến trúc này cân bằng giữa sự đơn giản trong triển khai và khả năng bảo trì, mở rộng ở mức độ vừa phải.

## Sơ đồ Kiến trúc Tổng thể

```mermaid
graph TD
    Client[Client (Web Browser / API Client)] --> Nginx[Web Server / Reverse Proxy (Optional)];
    Nginx --> AppServer[Flask App Server (Gunicorn/Waitress)];
    AppServer --> FlaskApp[Flask Application (src/__init__.py)];
    
    FlaskApp --> AuthBP[Auth Blueprint (/auth)];
    FlaskApp --> AudioBP[Audio Blueprint (/audio)];
    
    AuthBP --> AuthModels[Auth Models (src/blueprints/auth/models.py)];
    AuthModels --> Argon2[Argon2 (Password Hashing)];
    AuthModels --> PyJWT[PyJWT (Token Generation)];
    AuthModels --> SMTPLib[SMTPLib (Email 2FA)];
    AuthModels --> MongoDB[(MongoDB - Users Collection)];
    
    AudioBP --> AudioRoutes[Audio Routes (src/blueprints/audio/routes.py)];
    AudioRoutes --> Storage[Storage Module (src/core/storage.py)];
    AudioRoutes --> AESGCM[AES-GCM Module (src/core/encryption/aes_gcm.py)];
    AudioRoutes --> Chaotic[Chaotic Stream Module (src/core/encryption/chaotic.py)];
    
    Storage --> MongoDB_Files[(MongoDB - Files Metadata Collection)];
    Storage --> FileSystem[(File System - Stored Audio Files)];
    
    AESGCM --> CryptographyLib[cryptography Library];
    Chaotic --> NumpyLib[numpy Library];
    Chaotic --> Hashlib[hashlib (SHA256)];

    AppServer --> Config[Configuration (config.py / .env)];
    FlaskApp -- Reads --> Config;
    AuthModels -- Reads --> Config;

    style Client fill:#f9f,stroke:#333,stroke-width:2px
    style Nginx fill:#ccf,stroke:#333,stroke-width:2px
    style AppServer fill:#ccf,stroke:#333,stroke-width:2px
    style FlaskApp fill:#cdf,stroke:#333,stroke-width:2px
    style AuthBP fill:#ffc,stroke:#333,stroke-width:1px
    style AudioBP fill:#ffc,stroke:#333,stroke-width:1px
    style MongoDB fill:#cff,stroke:#333,stroke-width:2px
    style MongoDB_Files fill:#cff,stroke:#333,stroke-width:2px
    style FileSystem fill:#ddd,stroke:#333,stroke-width:2px
```

## Thành phần chính

1.  **`src/__init__.py` (Application Factory):**
    *   Sử dụng pattern Application Factory (`create_app`) để khởi tạo và cấu hình instance Flask.
    *   Tải cấu hình từ `config.py` dựa trên môi trường (development, testing, production).
    *   Khởi tạo kết nối cơ sở dữ liệu MongoDB.
    *   Đăng ký các Blueprints (Auth, Audio).
    *   Cung cấp các route cơ bản (ví dụ: `/ping`).

2.  **`config.py` & `.env`:**
    *   `config.py`: Định nghĩa các lớp cấu hình cho các môi trường khác nhau (DevelopmentConfig, TestingConfig, ProductionConfig).
    *   `.env`: Lưu trữ các thông tin nhạy cảm và cấu hình cụ thể cho môi trường (SECRET_KEY, MONGO_URI, MAIL_...). Sử dụng `python-dotenv` để tải các biến này.

3.  **Blueprints (`src/blueprints/`):**
    *   **`auth`:** Chứa logic liên quan đến xác thực người dùng.
        *   `models.py`: Lớp `User` xử lý đăng ký, đăng nhập, băm mật khẩu (Argon2), quản lý session, tạo JWT, xử lý 2FA (gửi mail, xác thực OTP).
        *   `routes.py`: Định nghĩa các API endpoint cho `/auth/signup`, `/auth/login`, `/auth/verify-2fa`, `/auth/logout`.
    *   **`audio`:** Chứa logic liên quan đến quản lý và mã hóa/giải mã tệp âm thanh.
        *   `routes.py`: Định nghĩa các API endpoint cho `/audio/upload`, `/audio/encrypt`, `/audio/decrypt`, `/audio/download`, `/audio/files`.
        *   Logic xử lý file và gọi các module mã hóa/lưu trữ.

4.  **Core Modules (`src/core/`):**
    *   **`encryption`:** Chứa logic mã hóa độc lập.
        *   `aes_gcm.py`: Implement mã hóa/giải mã bằng AES-256-GCM sử dụng thư viện `cryptography`. Tạo key/nonce an toàn.
        *   `chaotic.py`: Implement mã hóa/giải mã dòng bằng Logistic Map. Tạo keystream, XOR dữ liệu, tính toán và kiểm tra hash SHA-256.
    *   **`storage.py`:** Xử lý việc lưu trữ tệp vật lý và metadata trong MongoDB.
        *   Lưu tệp tải lên vào hệ thống tệp (filesystem).
        *   Lưu/truy xuất metadata (thông tin tệp, user ID, key/nonce/hash, trạng thái mã hóa/giải mã) vào collection `files` trong MongoDB.
        *   Cung cấp các hàm để lấy đường dẫn an toàn, kiểm tra quyền sở hữu.

5.  **Database (MongoDB):**
    *   **`users` collection:** Lưu trữ thông tin người dùng (ID, tên, email, mật khẩu đã hash, role, thời gian tạo).
    *   **`files` collection:** Lưu trữ metadata của các tệp âm thanh (ID, user ID, tên gốc, đường dẫn lưu trữ, trạng thái mã hóa/giải mã, thông tin cần thiết cho giải mã như key/nonce/hash/params).

6.  **Testing (`tests/`):**
    *   Sử dụng `pytest`.
    *   `conftest.py`: Chứa các fixtures dùng chung (ví dụ: tạo app context, client test, tạo dữ liệu mẫu).
    *   `test_factory.py`: Kiểm tra việc tạo app và cấu hình.
    *   `test_auth.py`: Kiểm tra các chức năng đăng ký, đăng nhập, 2FA, đăng xuất.
    *   `test_audio_aes.py`: Kiểm tra chu trình mã hóa/giải mã AES-GCM, xử lý lỗi.
    *   `test_audio_chaotic.py`: Kiểm tra chu trình mã hóa/giải mã Chaotic Stream, xử lý lỗi, kiểm tra toàn vẹn.

## Luồng dữ liệu chính

1.  **Đăng ký:** Client -> `/auth/signup` -> `AuthRoutes` -> `AuthModels.signup` -> Hash password -> Check DB -> Insert User -> Response.
2.  **Đăng nhập & 2FA:**
    *   Client -> `/auth/login` -> `AuthRoutes` -> `AuthModels.login` -> Check User -> Verify Password -> `AuthModels.send_2fa_code` -> Send Email (or suppress) -> Response (requires_2fa).
    *   Client -> `/auth/verify-2fa` (with OTP) -> `AuthRoutes` -> `AuthModels.verify_2fa` -> Check OTP & Expiry -> `AuthModels.start_session` -> Generate JWT -> Set Session -> Response (user info + token).
3.  **Upload Audio:** Client (with Auth Token) -> `/audio/upload` -> `AudioRoutes` -> Check Auth -> `Storage.save_uploaded_file` -> Save to Filesystem -> `Storage.save_file_metadata` -> Save to MongoDB -> Response (file_id).
4.  **Encrypt Audio:** Client (with Auth Token) -> `/audio/encrypt/<id>/<alg>` -> `AudioRoutes` -> Check Auth & File -> Get Original File Path & Metadata -> Call `encrypt_audio` (AES or Chaotic) -> `Storage.save_encrypted_file` -> Save to Filesystem -> `Storage.update_encryption_metadata` (save key/nonce/hash) -> Update MongoDB -> Response.
5.  **Decrypt Audio:** Client (with Auth Token) -> `/audio/decrypt/<id>` -> `AudioRoutes` -> Check Auth & File -> Get Encrypted File Path & Metadata (key/nonce/hash/params) -> Call `decrypt_audio` (AES or Chaotic) -> Check Integrity (AES tag / Chaotic hash) -> `Storage.save_decrypted_file` -> Save to Filesystem -> `Storage.update_decryption_status` -> Update MongoDB -> Response.

## Quyết định Thiết kế

*   **Argon2 for Password Hashing:** Chọn Argon2 vì tính an toàn và khả năng chống lại các cuộc tấn công GPU tốt hơn so với bcrypt hoặc PBKDF2.
*   **AES-GCM:** Chọn AES-GCM vì nó cung cấp cả mã hóa và xác thực (tính toàn vẹn và xác thực nguồn gốc) trong một bước, là chuẩn công nghiệp hiện đại.
*   **Chaotic Stream Cipher:** Bao gồm để trình diễn khái niệm, nhưng sử dụng Logistic Map đơn giản với cảnh báo về tính an toàn. Kết hợp SHA-256 để kiểm tra toàn vẹn vì bản thân mã hóa dòng không cung cấp điều này.
*   **JWT for API Authentication:** Sử dụng JWT (lưu trong session và trả về client) để xác thực các yêu cầu API sau khi đăng nhập, phù hợp cho các client không duy trì session cookie (ví dụ: mobile app, SPA).
*   **MongoDB:** Chọn MongoDB vì tính linh hoạt trong lưu trữ metadata, đặc biệt là khi cấu trúc metadata có thể thay đổi (ví dụ: lưu trữ key/nonce/hash khác nhau cho các thuật toán).
*   **Application Factory & Blueprints:** Giúp mã nguồn có tổ chức, dễ kiểm thử và tiềm năng mở rộng.
*   **Explicit Error Handling:** Cố gắng bắt và xử lý các lỗi cụ thể (ví dụ: `InvalidTag`, `VerifyMismatchError`, `FileNotFoundError`) để cung cấp phản hồi lỗi rõ ràng hơn.
*   **File Handling:** Lưu trữ tệp vật lý trên filesystem và metadata trong DB là một cách tiếp cận phổ biến, cân bằng giữa hiệu năng truy cập tệp và khả năng truy vấn metadata.

---
*(Tài liệu này cung cấp cái nhìn tổng quan về kiến trúc. Các chi tiết cụ thể hơn có thể được tìm thấy trong mã nguồn và các chú thích.)*

