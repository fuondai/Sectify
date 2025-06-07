/**
 * Xử lý xác thực người dùng (đăng nhập, đăng ký, 2FA)
 */

document.addEventListener('DOMContentLoaded', function() {
    // Xử lý form đăng nhập
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const loginAlert = document.getElementById('login-alert');
            
            // Kiểm tra đầu vào
            if (!email || !password) {
                showAlert(loginAlert, 'Vui lòng nhập đầy đủ email và mật khẩu', 'danger');
                return;
            }
            
            // Hiển thị trạng thái đang đăng nhập
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Đang đăng nhập...';
            
            // Gửi yêu cầu đăng nhập
            try {
                fetch('/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({
                        'email': email,
                        'password': password
                    })
                })
                .then(response => {
                    console.log('Trạng thái phản hồi đăng nhập:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('Dữ liệu phản hồi đăng nhập:', data);
                    if (data.error) {
                        showAlert(loginAlert, data.error, 'danger');
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                    } else if (data.message && data.requires_2fa) {
                        // Hiển thị OTP từ console cho người dùng trong môi trường development
                        const consoleOutput = document.querySelector('.console-output');
                        if (consoleOutput) {
                            consoleOutput.textContent = 'Kiểm tra console để biết mã OTP (chỉ trong môi trường development)';
                            consoleOutput.classList.remove('d-none');
                        }
                        
                        // Chuyển sang form nhập OTP
                        document.getElementById('login-form').classList.add('d-none');
                        document.getElementById('otp-form').classList.remove('d-none');
                        
                        // Không vô hiệu hóa nút đăng nhập khi chuyển sang form OTP
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                    } else if (data.message) {
                        // Đăng nhập thành công không cần 2FA (hiếm khi xảy ra)
                        showAlert(loginAlert, data.message, 'success');
                        setTimeout(() => {
                            window.location.href = '/';
                        }, 1000);
                    } else {
                        // Trường hợp không xác định, kích hoạt lại nút
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                        showAlert(loginAlert, 'Phản hồi không xác định từ máy chủ', 'warning');
                    }
                })
                .catch(error => {
                    console.error('Lỗi khi đăng nhập:', error);
                    showAlert(loginAlert, 'Đã xảy ra lỗi khi đăng nhập. Vui lòng thử lại sau.', 'danger');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                });
            } catch (e) {
                console.error('Lỗi exception khi đăng nhập:', e);
                showAlert(loginAlert, 'Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.', 'danger');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    }
    
    // Xử lý form nhập OTP
    const otpForm = document.getElementById('otpForm');
    if (otpForm) {
        otpForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const otp = document.getElementById('otp').value;
            const loginAlert = document.getElementById('login-alert');
            
            // Kiểm tra đầu vào
            if (!otp) {
                showAlert(loginAlert, 'Vui lòng nhập mã OTP', 'danger');
                return;
            }
            
            // Hiển thị trạng thái đang xác thực
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Đang xác thực...';
            
            // Gửi yêu cầu xác thực
            try {
                fetch('/auth/verify-2fa', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({
                        'otp': otp
                    })
                })
                .then(response => {
                    console.log('Trạng thái phản hồi xác thực OTP:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('Dữ liệu phản hồi xác thực OTP:', data);
                    
                    if (data.error) {
                        // Xác thực thất bại
                        showAlert(loginAlert, data.error, 'danger');
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                    } else if (data.success) {
                        // Xác thực thành công
                        showAlert(loginAlert, data.message || 'Xác thực thành công! Đang chuyển hướng...', 'success');
                        
                        // Chuyển hướng về trang chủ sau 1 giây
                        setTimeout(() => {
                            window.location.href = '/';
                        }, 1000);
                    } else {
                        // Trường hợp không xác định
                        showAlert(loginAlert, 'Có lỗi xảy ra khi xác thực. Vui lòng thử lại.', 'danger');
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                    }
                })
                .catch(error => {
                    console.error('Lỗi xác thực OTP:', error);
                    showAlert(loginAlert, 'Lỗi kết nối máy chủ. Vui lòng thử lại sau.', 'danger');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                });
            } catch (error) {
                console.error('Lỗi xác thực OTP:', error);
                showAlert(loginAlert, 'Lỗi không xác định. Vui lòng thử lại sau.', 'danger');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    }
    
    // Xử lý form đăng ký
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirmPassword');
        const passwordStrength = document.getElementById('password-strength');
        
        // Kiểm tra độ mạnh mật khẩu khi nhập
        if (passwordInput && passwordStrength) {
            passwordInput.addEventListener('input', function() {
                const strength = checkPasswordStrength(this.value);
                updatePasswordStrengthUI(strength, passwordStrength);
            });
        }
        
        // Kiểm tra khớp mật khẩu khi nhập
        if (confirmPasswordInput && passwordInput) {
            confirmPasswordInput.addEventListener('input', function() {
                if (this.value && this.value !== passwordInput.value) {
                    this.classList.add('is-invalid');
                } else {
                    this.classList.remove('is-invalid');
                }
            });
        }
        
        // Xử lý submit form
        signupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const signupAlert = document.getElementById('signup-alert');
            
            // Kiểm tra đầu vào
            if (!username || !email || !password || !confirmPassword) {
                showAlert(signupAlert, 'Vui lòng điền đầy đủ thông tin', 'danger');
                return;
            }
            
            if (password !== confirmPassword) {
                showAlert(signupAlert, 'Mật khẩu xác nhận không khớp', 'danger');
                return;
            }
            
            // Kiểm tra độ mạnh mật khẩu
            const passwordStrength = checkPasswordStrength(password);
            if (passwordStrength.score < 2) {
                showAlert(signupAlert, 'Mật khẩu không đủ mạnh. ' + passwordStrength.feedback, 'danger');
                return;
            }
            
            // Hiển thị trạng thái đang đăng ký
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Đang đăng ký...';
            
            // Gửi yêu cầu đăng ký
            try {
                fetch('/auth/signup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({
                        'name': username,
                        'email': email,
                        'password': password
                    })
                })
                .then(response => {
                    console.log('Trạng thái phản hồi đăng ký:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('Dữ liệu phản hồi đăng ký:', data);
                    if (data.error) {
                        showAlert(signupAlert, data.error, 'danger');
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                    } else if (data.message) {
                        showAlert(signupAlert, data.message, 'success');
                        // Chuyển hướng đến trang đăng nhập sau 2 giây
                        setTimeout(() => {
                            window.location.href = '/auth/login';
                        }, 2000);
                    } else {
                        // Trường hợp phản hồi không có error hoặc message
                        showAlert(signupAlert, 'Đăng ký thành công! Đang chuyển hướng...', 'success');
                        setTimeout(() => {
                            window.location.href = '/auth/login';
                        }, 2000);
                    }
                })
                .catch(error => {
                    console.error('Lỗi khi đăng ký:', error);
                    showAlert(signupAlert, 'Đã xảy ra lỗi khi đăng ký. Vui lòng thử lại sau.', 'danger');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                });
            } catch (e) {
                console.error('Lỗi exception khi đăng ký:', e);
                showAlert(signupAlert, 'Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.', 'danger');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    }
});

/**
 * Hiển thị thông báo
 * @param {HTMLElement} alertElement - Phần tử HTML hiển thị thông báo
 * @param {string} message - Nội dung thông báo
 * @param {string} type - Loại thông báo (danger, success, warning, info)
 */
function showAlert(alertElement, message, type = 'danger') {
    alertElement.textContent = message;
    alertElement.className = `alert alert-${type}`;
    alertElement.classList.remove('d-none');
    
    // Tự động ẩn thông báo sau 5 giây nếu là thông báo thành công
    if (type === 'success') {
        setTimeout(() => {
            alertElement.classList.add('d-none');
        }, 5000);
    }
}

/**
 * Kiểm tra độ mạnh của mật khẩu
 * @param {string} password - Mật khẩu cần kiểm tra
 * @returns {Object} - Thông tin về độ mạnh mật khẩu
 */
function checkPasswordStrength(password) {
    let score = 0;
    let feedback = '';
    
    // Kiểm tra độ dài
    if (password.length < 8) {
        feedback = 'Mật khẩu phải có ít nhất 8 ký tự.';
    } else {
        score += 1;
    }
    
    // Kiểm tra chữ thường
    if (/[a-z]/.test(password)) {
        score += 1;
    }
    
    // Kiểm tra chữ hoa
    if (/[A-Z]/.test(password)) {
        score += 1;
    }
    
    // Kiểm tra số
    if (/[0-9]/.test(password)) {
        score += 1;
    }
    
    // Kiểm tra ký tự đặc biệt
    if (/[^A-Za-z0-9]/.test(password)) {
        score += 1;
    }
    
    // Đánh giá độ mạnh
    let strength = '';
    if (score < 2) {
        strength = 'weak';
        feedback = 'Mật khẩu yếu. Cần thêm chữ hoa, chữ thường, số và ký tự đặc biệt.';
    } else if (score < 4) {
        strength = 'medium';
        feedback = 'Mật khẩu trung bình. Thử thêm chữ hoa, số hoặc ký tự đặc biệt.';
    } else {
        strength = 'strong';
        feedback = 'Mật khẩu mạnh!';
    }
    
    return {
        score,
        strength,
        feedback
    };
}

/**
 * Cập nhật giao diện hiển thị độ mạnh mật khẩu
 * @param {Object} strength - Thông tin độ mạnh mật khẩu
 * @param {HTMLElement} element - Phần tử HTML hiển thị độ mạnh
 */
function updatePasswordStrengthUI(strength, element) {
    let className = '';
    let width = '0%';
    
    switch (strength.strength) {
        case 'weak':
            className = 'bg-danger';
            width = '25%';
            break;
        case 'medium':
            className = 'bg-warning';
            width = '50%';
            break;
        case 'strong':
            className = 'bg-success';
            width = '100%';
            break;
        default:
            className = 'bg-danger';
            width = '0%';
    }
    
    element.innerHTML = `
        <div class="progress mb-2" style="height: 5px;">
            <div class="progress-bar ${className}" role="progressbar" style="width: ${width}" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
        <small class="text-muted">${strength.feedback}</small>
    `;
} 