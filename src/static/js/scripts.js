/**
 * scripts.js - Các chức năng chung cho toàn bộ ứng dụng Sectify
 */

document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo các sự kiện và xử lý giao diện chung
    initSidebar();
    initTooltips();
    handleThemePreference();
    setupGlobalEvents();
    handleAlerts();
});

/**
 * Khởi tạo sidebar và các sự kiện liên quan
 */
function initSidebar() {
    // Đánh dấu liên kết hiện tại trong sidebar
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath === href || (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('active');
        }
    });

    // Hiện/ẩn sidebar trên thiết bị di động
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('active');
        });
    }
}

/**
 * Khởi tạo các tooltip Bootstrap
 */
function initTooltips() {
    // Khởi tạo tooltip Bootstrap nếu tồn tại
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
    }
}

/**
 * Xử lý các thông báo và cảnh báo
 */
function handleAlerts() {
    // Tự động ẩn các thông báo sau 5 giây
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.add('fade-out');
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 500);
            }
        }, 5000);
    });

    // Xử lý nút đóng thông báo
    document.querySelectorAll('.alert .close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const alert = this.closest('.alert');
            alert.classList.add('fade-out');
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 500);
        });
    });
}

/**
 * Xử lý giao diện theo chế độ sáng/tối
 */
function handleThemePreference() {
    // Kiểm tra và áp dụng chế độ tối nếu người dùng đã chọn
    const darkModeEnabled = localStorage.getItem('darkMode') === 'true';
    if (darkModeEnabled) {
        document.body.classList.add('dark-mode');
    }

    // Nút chuyển đổi chế độ tối
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            const isDarkMode = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode);
            updateDarkModeIcon(isDarkMode);
        });

        // Cập nhật icon dựa trên trạng thái hiện tại
        updateDarkModeIcon(darkModeEnabled);
    }
}

/**
 * Cập nhật biểu tượng chế độ tối
 */
function updateDarkModeIcon(isDarkMode) {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        if (isDarkMode) {
            darkModeToggle.innerHTML = '<i class="fa-solid fa-sun"></i>';
            darkModeToggle.setAttribute('title', 'Chuyển sang chế độ sáng');
        } else {
            darkModeToggle.innerHTML = '<i class="fa-solid fa-moon"></i>';
            darkModeToggle.setAttribute('title', 'Chuyển sang chế độ tối');
        }
        
        // Cập nhật tooltip nếu có
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltip = bootstrap.Tooltip.getInstance(darkModeToggle);
            if (tooltip) {
                tooltip.dispose();
                new bootstrap.Tooltip(darkModeToggle);
            }
        }
    }
}

/**
 * Thiết lập các sự kiện chung cho toàn bộ ứng dụng
 */
function setupGlobalEvents() {
    // Xử lý sự kiện nút logout
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Bạn có chắc chắn muốn đăng xuất?')) {
                window.location.href = this.getAttribute('href');
            }
        });
    }

    // Xử lý thanh tìm kiếm toàn cầu nếu có
    const globalSearch = document.getElementById('global-search');
    if (globalSearch) {
        globalSearch.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                const searchTerm = this.value.trim();
                if (searchTerm) {
                    window.location.href = `/search?q=${encodeURIComponent(searchTerm)}`;
                }
            }
        });
    }
}

/**
 * Tạo một thông báo
 * @param {string} message Nội dung thông báo
 * @param {string} type Loại thông báo (success, error, warning, info)
 * @param {string} container Selector của phần tử chứa thông báo
 */
function showAlert(message, type = 'info', container = '#alert-container') {
    const alertContainer = document.querySelector(container);
    if (!alertContainer) return;

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';

    // Icon dựa vào loại thông báo
    let icon = '';
    switch (type) {
        case 'success':
            icon = '<i class="fa-solid fa-check-circle me-2"></i>';
            break;
        case 'error':
        case 'danger':
            icon = '<i class="fa-solid fa-exclamation-circle me-2"></i>';
            break;
        case 'warning':
            icon = '<i class="fa-solid fa-exclamation-triangle me-2"></i>';
            break;
        default:
            icon = '<i class="fa-solid fa-info-circle me-2"></i>';
    }

    alertDiv.innerHTML = `
        ${icon}${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    alertContainer.appendChild(alertDiv);

    // Tự động ẩn sau 5 giây
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.classList.add('fade-out');
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.parentNode.removeChild(alertDiv);
                }
            }, 500);
        }
    }, 5000);
}

/**
 * Format thời gian dạng mm:ss từ số giây
 * @param {number} seconds Số giây
 * @returns {string} Chuỗi thời gian dạng mm:ss
 */
function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format kích thước file sang dạng dễ đọc
 * @param {number} bytes Kích thước file theo byte
 * @returns {string} Kích thước file dạng dễ đọc
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Lấy đuôi file từ tên file
 * @param {string} filename Tên file
 * @returns {string} Đuôi file
 */
function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
}

/**
 * Kiểm tra xem file có phải là file âm thanh hỗ trợ không
 * @param {string} filename Tên file
 * @returns {boolean} True nếu là file âm thanh hỗ trợ
 */
function isSupportedAudioFile(filename) {
    const extension = getFileExtension(filename);
    return ['wav', 'mp3', 'ogg', 'flac'].includes(extension);
}

/**
 * Tạo element từ HTML string
 * @param {string} html HTML string
 * @returns {Element} Element được tạo
 */
function createElementFromHTML(html) {
    const div = document.createElement('div');
    div.innerHTML = html.trim();
    return div.firstChild;
}

$(document).ready(function() {
  $("form[name=signup_form]").submit(function(e) {
    var $form = $(this);
    var $error = $form.find(".error");
    var data = $form.serialize();

    $.ajax({
      url: "/user/signup",
      type: "POST",
      data: data,
      dataType: "json",
      success: function(resp) {
        window.location.href = "/login/";
      },
      error: function(resp) {
        $error.text(resp.responseJSON.error).removeClass("error--hidden");
      }
    });

    e.preventDefault();
  });

  $("form[name=login_form]").submit(function(e) {
    var $form = $(this);
    var $error = $form.find(".error");
    var data = $form.serialize();

    $.ajax({
      url: "/user/login",
      type: "POST",
      data: data,
      dataType: "json",
      success: function(resp) {
        // Check if 2FA is required
        if (resp.requires_2fa) {
          window.location.href = "/user/verify_2fa";
        } else {
          window.location.href = "/dashboard/";
        }
      },
      error: function(resp) {
        $error.text(resp.responseJSON.error).removeClass("error--hidden");
      }
    });

    e.preventDefault();
  });

  $("form[name=2fa_form]").submit(function(e) {
    var $form = $(this);
    var $error = $form.find(".error");
    var data = $form.serialize();

    $.ajax({
      url: "/user/verify_2fa",
      type: "POST",
      data: data,
      dataType: "json",
      success: function(resp) {
        window.location.href = "/dashboard/";
      },
      error: function(resp) {
        $error.text(resp.responseJSON.error).removeClass("error--hidden");
      }
    });

    e.preventDefault();
  });
});
