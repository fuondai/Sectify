# Sectify - Nền tảng Streaming Âm thanh An toàn

**Sectify** là một dự án minh chứng (Proof-of-Concept) được xây dựng để trình diễn các kỹ thuật tiên tiến trong việc bảo vệ và phân phối nội dung âm thanh số. Nền tảng này không chỉ là một trình phát nhạc thông thường, mà là một hệ thống hoàn chỉnh với nhiều lớp bảo mật, được thiết kế để chống lại các hành vi truy cập trái phép, ngăn chặn rò rỉ và bảo vệ tài sản số của người sở hữu nội dung.

Dự án tích hợp các công nghệ và khái niệm bảo mật hàng đầu như: **FastAPI**, **HLS (HTTP Live Streaming)**, mã hóa **AES-256**, **Digital Watermarking** (Đóng dấu số) theo thời gian thực, và các thuật toán mật mã tùy chỉnh.

## Mục tiêu chính

- **Bảo vệ toàn vẹn cho tài sản gốc:** Đảm bảo các tệp âm thanh gốc không bao giờ bị lộ hoặc truy cập trực tiếp.
- **Kiểm soát truy cập nghiêm ngặt:** Chỉ những người dùng đã được xác thực và cấp phép mới có thể truy cập nội dung.
- **Chống sao chép và phân phối trái phép:** Sử dụng công nghệ đóng dấu số (watermarking) để truy vết nguồn gốc rò rỉ.
- **Đảm bảo trải nghiệm người dùng:** Cung cấp streaming chất lượng cao, mượt mà mà không làm ảnh hưởng đến tính bảo mật.

## Kiến trúc & Công nghệ

- **Backend:** **FastAPI (Python)**, được lựa chọn vì hiệu năng vượt trội, khả năng xử lý bất đồng bộ (async) và hệ sinh thái mạnh mẽ, rất phù hợp cho các ứng dụng I/O-bound như streaming.
- **Database:** **MongoDB**, một cơ sở dữ liệu NoSQL linh hoạt, giúp lưu trữ thông tin người dùng, metadata của track nhạc và các khóa mã hóa một cách hiệu quả.
- **Streaming Protocol:** **HLS (HTTP Live Streaming)**, chia nhỏ tệp âm thanh thành các đoạn ngắn và phân phối qua HTTP, giúp tương thích với hầu hết các thiết bị và dễ dàng vượt qua các tường lửa.
- **Frontend:** **Vanilla JavaScript, HTML5, CSS3**, giữ cho giao diện đơn giản, nhẹ và tập trung vào việc trình diễn các tính năng bảo mật phức tạp ở backend.

## Phân tích sâu về các Cơ chế Bảo mật

Sectify triển khai một mô hình bảo mật đa lớp, lấy cảm hứng từ triết lý "Zero Trust". Mỗi yêu cầu truy cập đều được kiểm tra và xác thực một cách độc lập.

### Lớp 1: Mã hóa khi lưu trữ (Encryption at Rest) - Chaotic Stream Cipher

Đây là lớp bảo vệ đầu tiên và quan trọng nhất, đảm bảo an toàn cho các tệp âm thanh gốc ngay cả khi máy chủ bị xâm nhập vật lý hoặc logic.

- **Vấn đề:** Nếu một kẻ tấn công có quyền truy cập vào hệ thống file của server, họ có thể lấy đi toàn bộ các tệp âm thanh gốc.
- **Giải pháp:** Chúng tôi không lưu trữ tệp gốc ở dạng "trần". Thay vào đó, mỗi tệp khi được tải lên sẽ được mã hóa bằng **Chaotic Stream Cipher**—một thuật toán mật mã dòng tùy chỉnh.
  - **Nguyên lý hoạt động:** Thuật toán này sử dụng các hàm số hỗn loạn (chaotic maps) để tạo ra một dòng khóa (keystream) giả ngẫu nhiên, không lặp lại và có độ phức tạp cao. Dòng khóa này sau đó được XOR với dữ liệu gốc để tạo ra bản mã.
  - **Key Derivation:** Khóa mã hóa cho mỗi tệp không phải là một chuỗi tĩnh. Nó được tạo ra một cách linh hoạt bằng thuật toán **PBKDF2-HMAC-SHA256** từ sự kết hợp của `user_id`, `track_id` và một `master_secret` của hệ thống. Điều này đảm bảo mỗi tệp có một khóa mã hóa duy nhất và việc xâm phạm một khóa không ảnh hưởng đến các tệp khác.
- **Triển khai:** Logic cốt lõi nằm trong `app/core/chaotic_audio_protection.py`.

### Lớp 2: Mã hóa khi truyền tải (Encryption in Transit) - HLS + AES-256

Lớp này bảo vệ dữ liệu trong quá trình được truyền từ server đến trình duyệt của người dùng.

- **Vấn đề:** Kẻ tấn công trên cùng mạng (Man-in-the-middle) có thể bắt gói tin và lấy nội dung streaming.
- **Giải pháp:** Sectify sử dụng HLS với mã hóa **AES-256** tiêu chuẩn công nghiệp.
  - **Quy trình:**
    1.  Tệp âm thanh được chia thành các đoạn (segment) nhỏ, thường dài vài giây.
    2.  Mỗi segment được mã hóa bằng một khóa AES-256 riêng.
    3.  Tệp `playlist.m3u8` (manifest) chứa thông tin về các segment và một URI để lấy khóa giải mã.
    4.  URI này trỏ đến một endpoint an toàn (`/api/v1/stream/key/...`) trên server của Sectify.
  - **Bảo vệ Key Delivery:** Endpoint trả về khóa giải mã được bảo vệ nghiêm ngặt:
    - Yêu cầu một **JSON Web Token (JWT)** hợp lệ, có thời gian sống ngắn.
    - Token được "gắn" với địa chỉ IP của người dùng, chống lại việc token bị đánh cắp và sử dụng ở nơi khác.
    - Sử dụng cơ chế "JIT Key Alias" (Just-in-Time Key Alias) để ngăn chặn việc đoán trước hoặc lạm dụng URL của khóa.

### Lớp 3: Truy vết và Ngăn chặn Rò rỉ - Dynamic Digital Watermarking

Đây là tuyến phòng thủ cuối cùng, giúp xác định nguồn gốc của một bản nhạc bị rò rỉ ra ngoài.

- **Vấn đề:** Một người dùng hợp pháp có thể sử dụng các công cụ để ghi lại luồng âm thanh và phân phối nó bất hợp pháp.
- **Giải pháp:** Sectify triển khai hệ thống đóng dấu số động (dynamic watermarking) cho mỗi phiên nghe nhạc.
  - **Nguyên lý hoạt động:** Khi một người dùng yêu cầu phát một bản nhạc, hệ thống sẽ:
    1.  Tạo ra một "dấu vân tay" (watermark) độc nhất dựa trên thông tin của người dùng (`user_id`) và phiên truy cập (`session_id`).
    2.  Watermark này là một chuỗi nhiễu tín hiệu không thể nghe thấy bằng tai thường, được tạo ra và nhúng vào một dải tần số rất cao (ví dụ: 17-19 kHz) của luồng âm thanh.
    3.  Quá trình này diễn ra "on-the-fly" (tức thời) trước khi các segment HLS được tạo ra.
  - **Truy vết:** Nếu một tệp âm thanh của Sectify bị phát hiện trên internet, quản trị viên có thể sử dụng script `scripts/test_watermark_extract.py` để phân tích tệp đó. Script sẽ trích xuất mẫu nhiễu, so sánh nó với cơ sở dữ liệu các watermark đã tạo và xác định chính xác người dùng đã làm rò rỉ nội dung.

### Lớp 4: Kiểm soát Truy cập và Xác thực Nâng cao

- **Centralized Authorization (`authorization.py`):** Mọi quyết định về quyền truy cập (có được phép stream track X không?) đều được xử lý bởi một service trung tâm. Điều này giúp chống lại lỗ hổng **IDOR (Insecure Direct Object References)**, đảm bảo người dùng không thể thay đổi ID trong URL để truy cập vào nội dung họ không có quyền.
- **Xác thực Hai Yếu tố (2FA/TOTP):** Người dùng có thể kích hoạt 2FA bằng các ứng dụng xác thực như Google Authenticator, tăng cường đáng kể an toàn cho tài khoản.
- **Rate Limiting:** Giới hạn số lần yêu cầu đến các endpoint nhạy cảm (như login, signup) để chống lại các cuộc tấn công brute-force.
- **Embed Protection:** Ngăn chặn việc nhúng trình phát nhạc lên các website không được cho phép bằng cách kiểm tra header `Origin` và `Referer`.

## Cài đặt và Chạy dự án

### Yêu cầu hệ thống:

- Python 3.10+
- **FFmpeg:** Một dependency hệ thống quan trọng, cần được cài đặt và thêm vào PATH. FFmpeg được sử dụng cho mọi tác vụ xử lý âm thanh (chia segment, đóng dấu, chuyển đổi định dạng).

### Các bước cài đặt:

1.  **Clone repository:**

    ```bash
    git clone https://github.com/fuondai/Sectify.git
    cd Sectify
    ```

2.  **Tạo và kích hoạt môi trường ảo:**

    ```bash
    python -m venv venv
    # Trên Windows
    .\venv\Scripts\activate
    # Trên macOS/Linux
    source venv/bin/activate
    ```

3.  **Cài đặt các gói phụ thuộc:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Cấu hình môi trường:**

    - Tạo một tệp `.env` ở thư mục gốc của dự án.
    - Sao chép nội dung từ một tệp `.env.example` (nếu có) hoặc thêm các biến cần thiết:

    ```env
    SECRET_KEY=... # Một chuỗi bí mật dài và ngẫu nhiên
    MONGO_DETAILS="mongodb://localhost:27017" # Chuỗi kết nối MongoDB
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    ```

5.  **Thiết lập thư mục:**
    Chạy script để tạo các thư mục cần thiết cho việc lưu trữ file HLS, uploads, v.v.

    ```bash
    python scripts/setup_directories.py
    ```

6.  **Chạy ứng dụng:**
    ```bash
    python run.py
    ```
    Ứng dụng sẽ chạy tại `http://127.0.0.1:8000`.

## Cấu trúc thư mục

```
Sectify/
├── app/                  # Thư mục chính chứa mã nguồn ứng dụng FastAPI
│   ├── api/              # Định nghĩa các API endpoints
│   ├── core/             # Logic cốt lõi (xác thực, mã hóa, watermarking)
│   ├── crud/             # Các hàm tương tác với CSDL (Create, Read, Update, Delete)
│   ├── db/               # Cấu hình và kết nối CSDL
│   ├── schemas/          # Các mô hình dữ liệu Pydantic
│   ├── static/           # Tài sản tĩnh (JS, CSS)
│   ├── templates/        # Các template HTML (Jinja2)
│   └── main.py           # File khởi tạo ứng dụng FastAPI
├── hls/                  # Nơi lưu trữ các segment và playlist HLS đã xử lý
├── scripts/              # Các script tiện ích (thiết lập, kiểm tra watermark)
├── uploads_encrypted/    # Nơi lưu các tệp âm thanh gốc đã được mã hóa
├── .env                  # File cấu hình biến môi trường (cần tự tạo)
├── requirements.txt      # Danh sách các gói phụ thuộc Python
└── run.py                # Script để chạy ứng dụng
```
