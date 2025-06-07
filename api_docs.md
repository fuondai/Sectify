# Tài liệu API - Ứng dụng Mã hóa Âm thanh

## Giới thiệu

Tài liệu này mô tả chi tiết các API endpoint được cung cấp bởi ứng dụng mã hóa âm thanh. Tất cả các endpoint (ngoại trừ đăng ký và đăng nhập ban đầu) đều yêu cầu xác thực thông qua JWT token được gửi trong header `Authorization` dưới dạng `Bearer <token>`.

## Xác thực (`/auth`)

### 1. Đăng ký người dùng

*   **Endpoint:** `POST /auth/signup`
*   **Mô tả:** Tạo một tài khoản người dùng mới.
*   **Request Body (form-data):**
    *   `name` (string, required): Tên người dùng.
    *   `email` (string, required): Địa chỉ email (duy nhất).
    *   `password` (string, required): Mật khẩu (ít nhất 8 ký tự).
*   **Response (Success - 201 Created):**
    ```json
    {
        "message": "Đăng ký thành công. Vui lòng đăng nhập."
    }
    ```
*   **Response (Error - 400 Bad Request):**
    *   Thiếu trường bắt buộc:
        ```json
        {
            "error": "Thiếu các trường bắt buộc (name, email, password)"
        }
        ```
    *   Mật khẩu quá ngắn:
        ```json
        {
            "error": "Mật khẩu phải có ít nhất 8 ký tự"
        }
        ```
    *   Email đã tồn tại:
        ```json
        {
            "error": "Địa chỉ email đã được sử dụng"
        }
        ```
*   **Response (Error - 500 Internal Server Error):**
    ```json
    {
        "error": "Không thể bảo mật mật khẩu" // Hoặc lỗi DB khác
    }
    ```

### 2. Đăng nhập (Bắt đầu 2FA)

*   **Endpoint:** `POST /auth/login`
*   **Mô tả:** Xác thực thông tin đăng nhập ban đầu và gửi mã OTP 2FA qua email.
*   **Request Body (form-data):**
    *   `email` (string, required): Địa chỉ email.
    *   `password` (string, required): Mật khẩu.
*   **Response (Success - 200 OK - Yêu cầu 2FA):**
    ```json
    {
        "message": "Yêu cầu xác thực hai yếu tố",
        "requires_2fa": true
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Yêu cầu email và mật khẩu"
    }
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Thông tin đăng nhập không hợp lệ"
    }
    ```
*   **Response (Error - 500 Internal Server Error):**
    ```json
    {
        "error": "Không thể gửi mã xác thực" // Hoặc lỗi khác
    }
    ```

### 3. Xác thực 2FA

*   **Endpoint:** `POST /auth/verify-2fa`
*   **Mô tả:** Xác thực mã OTP 2FA được gửi qua email để hoàn tất đăng nhập.
*   **Request Body (form-data):**
    *   `otp` (string, required): Mã OTP 6 chữ số người dùng nhập.
*   **Response (Success - 200 OK):**
    ```json
    {
        "_id": "user_id_hex",
        "name": "User Name",
        "email": "user@example.com",
        "role": "user",
        "token": "jwt_token_string"
    }
    ```
*   **Response (Error - 400 Bad Request):**
    *   Thiếu OTP:
        ```json
        {
            "error": "Missing OTP code in form data"
        }
        ```
    *   Phiên hết hạn/không hợp lệ:
        ```json
        {
            "error": "Phiên xác thực đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại."
        }
        ```
    *   OTP hết hạn:
        ```json
        {
            "error": "Mã OTP đã hết hạn. Vui lòng đăng nhập lại."
        }
        ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Mã xác thực hai yếu tố không hợp lệ"
    }
    ```
*   **Response (Error - 404 Not Found):**
    ```json
    {
        "error": "Không tìm thấy người dùng"
    }
    ```
*   **Response (Error - 500 Internal Server Error):**
    ```json
    {
        "error": "Không thể tạo token phiên làm việc"
    }
    ```

### 4. Đăng xuất

*   **Endpoint:** `GET /auth/logout`
*   **Mô tả:** Xóa session của người dùng.
*   **Response (Success - 200 OK):**
    ```json
    {
        "message": "Đăng xuất thành công"
    }
    ```

---
*(Tiếp theo sẽ là tài liệu cho các endpoint `/audio`)*



## Quản lý Âm thanh (`/audio`)

**Yêu cầu xác thực:** Tất cả các endpoint trong phần này đều yêu cầu header `Authorization: Bearer <jwt_token>`.

### 5. Tải lên tệp âm thanh

*   **Endpoint:** `POST /audio/upload`
*   **Mô tả:** Tải lên một tệp âm thanh định dạng WAV để chuẩn bị mã hóa.
*   **Request Body (form-data):**
    *   `file` (file, required): Tệp âm thanh WAV cần tải lên.
*   **Response (Success - 201 Created):**
    ```json
    {
        "message": "Tệp đã được tải lên thành công.",
        "file_id": "generated_file_id_hex",
        "filename": "original_filename.wav"
    }
    ```
*   **Response (Error - 400 Bad Request):**
    *   Thiếu tệp:
        ```json
        {
            "error": "Không tìm thấy tệp trong yêu cầu"
        }
        ```
    *   Tệp không có tên hoặc không được phép:
        ```json
        {
            "error": "Tên tệp không hợp lệ hoặc không được phép"
        }
        ```
    *   Định dạng không phải WAV:
        ```json
        {
            "error": "Chỉ chấp nhận tệp định dạng WAV"
        }
        ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Token không hợp lệ hoặc đã hết hạn"
    }
    ```
*   **Response (Error - 500 Internal Server Error):**
    ```json
    {
        "error": "Lỗi lưu trữ tệp hoặc metadata"
    }
    ```

### 6. Mã hóa tệp âm thanh

*   **Endpoint:** `POST /audio/encrypt/<file_id>/<algorithm>`
*   **Mô tả:** Mã hóa một tệp âm thanh đã tải lên bằng thuật toán được chỉ định.
*   **Path Parameters:**
    *   `file_id` (string, required): ID của tệp đã tải lên (lấy từ response của `/audio/upload`).
    *   `algorithm` (string, required): Thuật toán mã hóa (`aes` hoặc `chaotic`).
*   **Response (Success - 200 OK):**
    ```json
    {
        "message": "Tệp đã được mã hóa thành công bằng [aes/chaotic].",
        "file_id": "file_id_hex",
        "algorithm": "[aes/chaotic]"
        // Có thể bao gồm đường dẫn tải xuống tệp mã hóa
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Thuật toán không hợp lệ. Chỉ hỗ trợ 'aes' hoặc 'chaotic'."
    }
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Token không hợp lệ hoặc đã hết hạn"
    }
    ```
*   **Response (Error - 404 Not Found):**
    ```json
    {
        "error": "Không tìm thấy tệp gốc hoặc bạn không có quyền truy cập"
    }
    ```
*   **Response (Error - 409 Conflict):**
    ```json
    {
        "error": "Tệp này đã được mã hóa bằng thuật toán này rồi"
    }
    ```
*   **Response (Error - 500 Internal Server Error):**
    ```json
    {
        "error": "Lỗi trong quá trình mã hóa hoặc lưu metadata"
    }
    ```

### 7. Giải mã tệp âm thanh

*   **Endpoint:** `POST /audio/decrypt/<file_id>`
*   **Mô tả:** Giải mã một tệp âm thanh đã được mã hóa trước đó.
*   **Path Parameters:**
    *   `file_id` (string, required): ID của tệp đã tải lên và mã hóa.
*   **Response (Success - 200 OK):**
    ```json
    {
        "message": "Tệp đã được giải mã thành công.",
        "file_id": "file_id_hex"
        // Có thể bao gồm đường dẫn tải xuống tệp giải mã
    }
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Token không hợp lệ hoặc đã hết hạn"
    }
    ```
*   **Response (Error - 404 Not Found):**
    ```json
    {
        "error": "Không tìm thấy tệp mã hóa hoặc metadata tương ứng, hoặc bạn không có quyền truy cập"
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Tệp chưa được mã hóa hoặc thiếu thông tin cần thiết để giải mã"
    }
    ```
*   **Response (Error - 500 Internal Server Error):**
    *   Lỗi giải mã (ví dụ: sai key/nonce/hash, dữ liệu bị thay đổi):
        ```json
        {
            "error": "Giải mã thất bại. Dữ liệu có thể đã bị thay đổi hoặc thông tin giải mã không chính xác."
        }
        ```
    *   Lỗi khác:
        ```json
        {
            "error": "Lỗi không mong muốn trong quá trình giải mã"
        }
        ```

### 8. Tải xuống tệp

*   **Endpoint:** `GET /audio/download/<file_id>/<type>`
*   **Mô tả:** Tải xuống phiên bản cụ thể của một tệp (gốc, mã hóa, giải mã).
*   **Path Parameters:**
    *   `file_id` (string, required): ID của tệp.
    *   `type` (string, required): Loại tệp cần tải (`original`, `encrypted`, `decrypted`).
*   **Response (Success - 200 OK):**
    *   Trả về nội dung tệp với `Content-Type` phù hợp (ví dụ: `audio/wav` cho original/decrypted, `application/octet-stream` cho encrypted) và header `Content-Disposition: attachment; filename=...`.
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Token không hợp lệ hoặc đã hết hạn"
    }
    ```
*   **Response (Error - 404 Not Found):**
    ```json
    {
        "error": "Không tìm thấy tệp hoặc phiên bản tệp yêu cầu, hoặc bạn không có quyền truy cập"
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Loại tệp không hợp lệ. Chỉ hỗ trợ 'original', 'encrypted', 'decrypted'."
    }
    ```

### 9. Liệt kê các tệp của người dùng

*   **Endpoint:** `GET /audio/files`
*   **Mô tả:** Lấy danh sách các tệp âm thanh đã tải lên bởi người dùng hiện tại.
*   **Response (Success - 200 OK):**
    ```json
    [
        {
            "_id": "file_id_1",
            "filename": "audio1.wav",
            "upload_date": "iso_timestamp",
            "encrypted_status": {
                "aes": true, // Đã mã hóa bằng AES
                "chaotic": false // Chưa mã hóa bằng Chaotic
            },
            "decrypted_status": {
                "aes": true, // Đã giải mã từ AES
                "chaotic": false // Chưa giải mã từ Chaotic
            }
        },
        {
            "_id": "file_id_2",
            "filename": "track2.wav",
            "upload_date": "iso_timestamp",
            "encrypted_status": {
                "aes": false,
                "chaotic": true
            },
            "decrypted_status": {
                "aes": false,
                "chaotic": true
            }
        }
        // ... các tệp khác
    ]
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Token không hợp lệ hoặc đã hết hạn"
    }
    ```
*   **Response (Error - 500 Internal Server Error):**
    ```json
    {
        "error": "Lỗi truy vấn cơ sở dữ liệu"
    }
    ```

---
*(Kết thúc tài liệu API)*

