/**
 * Xử lý tải lên tệp âm thanh
 */

document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadForm = document.getElementById('upload-form');
    const uploadFileList = document.getElementById('upload-file-list');
    const uploadQueueContainer = document.getElementById('upload-queue-container');
    
    // Các phần tử UI trong upload-area
    const uploadPlaceholder = document.getElementById('upload-placeholder');
    const uploadProgressContainer = document.getElementById('upload-progress-container');
    const uploadProgressBar = document.getElementById('upload-progress-bar');
    const uploadStatus = document.getElementById('upload-status');
    const uploadComplete = document.getElementById('upload-complete');
    const uploadAnother = document.getElementById('upload-another');
    
    // Xử lý drag and drop
    if (uploadArea) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                handleFiles(e.dataTransfer.files);
            }
        });
        
        uploadArea.addEventListener('click', function() {
            fileInput.click();
        });
    }
    
    // Xử lý chọn tệp
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                handleFiles(this.files);
            }
        });
    }
    
    // Xử lý nút "Tải lên file khác"
    if (uploadAnother) {
        uploadAnother.addEventListener('click', function() {
            resetUploadForm();
        });
    }
    
    // Tải danh sách file gần đây
    loadRecentUploads();
    
    /**
     * Xử lý tệp được chọn
     * @param {FileList} files - Danh sách tệp
     */
    function handleFiles(files) {
        const file = files[0]; // Chỉ xử lý tệp đầu tiên
        
        // Kiểm tra loại tệp
        if (!isAudioFile(file)) {
            showAlert('Chỉ hỗ trợ các tệp âm thanh .wav, .mp3, .ogg, .flac', 'danger');
            return;
        }
        
        // Kiểm tra kích thước tệp (tối đa 20MB)
        if (file.size > 20 * 1024 * 1024) {
            showAlert('Kích thước tệp vượt quá giới hạn (tối đa 20MB)', 'danger');
            return;
        }
        
        // Hiển thị giao diện tải lên
        uploadPlaceholder.classList.add('d-none');
        uploadProgressContainer.classList.remove('d-none');
        
        // Tạo FormData
        const formData = new FormData();
        formData.append('audio_file', file);
        
        // Tạo XMLHttpRequest để theo dõi tiến trình
        const xhr = new XMLHttpRequest();
        
        // Theo dõi tiến trình tải lên
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                uploadProgressBar.style.width = percentComplete + '%';
                uploadStatus.textContent = percentComplete + '% hoàn thành';
            }
        });
        
        // Xử lý khi tải lên hoàn tất
        xhr.addEventListener('load', function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    
                    if (response.success) {
                        // Tải lên thành công
                        uploadProgressContainer.classList.add('d-none');
                        uploadComplete.classList.remove('d-none');
                        
                        // Tải lại danh sách file gần đây
                        loadRecentUploads();
                    } else {
                        // Lỗi từ server
                        resetUploadForm();
                        showAlert(response.error || 'Không thể tải lên tệp âm thanh', 'danger');
                    }
                } catch (error) {
                    // Lỗi phân tích phản hồi
                    console.error('Lỗi phân tích phản hồi:', error);
                    resetUploadForm();
                    showAlert('Lỗi khi xử lý phản hồi từ server', 'danger');
                }
            } else {
                // Lỗi HTTP
                console.error('Lỗi HTTP:', xhr.status, xhr.statusText);
                resetUploadForm();
                showAlert('Lỗi khi tải lên: ' + xhr.status, 'danger');
            }
        });
        
        // Xử lý lỗi
        xhr.addEventListener('error', function() {
            console.error('Lỗi kết nối');
            resetUploadForm();
            showAlert('Đã xảy ra lỗi khi tải lên tệp', 'danger');
        });
        
        // Xử lý hủy
        xhr.addEventListener('abort', function() {
            resetUploadForm();
            showAlert('Tải lên đã bị hủy', 'warning');
        });
        
        // Gửi yêu cầu
        xhr.open('POST', '/audio/upload', true);
        xhr.send(formData);
    }
    
    /**
     * Tải danh sách tệp gần đây
     */
    function loadRecentUploads() {
        const recentUploadsList = document.getElementById('recent-uploads-list');
        if (!recentUploadsList) return;
        
        fetch('/audio/files')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Lỗi khi tải danh sách tệp');
                }
                return response.json();
            })
            .then(data => {
                if (data.success && data.files && data.files.length > 0) {
                    // Lấy 5 tệp gần đây nhất
                    const recentFiles = data.files.slice(0, 5);
                    
                    // Tạo HTML
                    let html = '<ul class="list-group">';
                    recentFiles.forEach(file => {
                        const date = new Date(file.upload_date).toLocaleDateString('vi-VN');
                        const status = getStatusBadge(file.status);
                        
                        html += `
                            <li class="list-group-item d-flex justify-content-between align-items-center bg-dark text-light border-secondary">
                                <div>
                                    <i class="fa-solid fa-music me-2 text-primary"></i>
                                    <span>${file.name}</span>
                                </div>
                                <div>
                                    ${status}
                                    <small class="text-muted ms-2">${date}</small>
                                </div>
                            </li>
                        `;
                    });
                    html += '</ul>';
                    
                    recentUploadsList.innerHTML = html;
                } else {
                    recentUploadsList.innerHTML = '<div class="text-center py-4"><p>Chưa có tệp nào được tải lên.</p></div>';
                }
            })
            .catch(error => {
                console.error('Lỗi:', error);
                recentUploadsList.innerHTML = '<div class="text-center py-4"><p class="text-danger">Không thể tải danh sách tệp.</p></div>';
            });
    }
    
    /**
     * Tạo badge trạng thái
     * @param {string} status - Trạng thái tệp
     * @returns {string} - HTML badge
     */
    function getStatusBadge(status) {
        let badgeClass = '';
        let badgeText = '';
        
        switch (status) {
            case 'original':
                badgeClass = 'bg-success';
                badgeText = 'Gốc';
                break;
            case 'encrypted':
                badgeClass = 'bg-danger';
                badgeText = 'Đã mã hóa';
                break;
            case 'decrypted':
                badgeClass = 'bg-info';
                badgeText = 'Đã giải mã';
                break;
            default:
                badgeClass = 'bg-secondary';
                badgeText = 'Không xác định';
        }
        
        return `<span class="badge ${badgeClass}">${badgeText}</span>`;
    }
    
    /**
     * Kiểm tra tệp có phải là tệp âm thanh hợp lệ
     * @param {File} file - Tệp cần kiểm tra
     * @returns {boolean} - true nếu là tệp âm thanh hợp lệ
     */
    function isAudioFile(file) {
        const validTypes = ['audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'audio/mp3'];
        const validExtensions = ['.wav', '.mp3', '.ogg', '.flac'];
        
        // Kiểm tra MIME type
        if (validTypes.includes(file.type)) {
            return true;
        }
        
        // Kiểm tra phần mở rộng
        const fileName = file.name.toLowerCase();
        return validExtensions.some(ext => fileName.endsWith(ext));
    }
    
    /**
     * Hiển thị thông báo
     * @param {string} message - Nội dung thông báo
     * @param {string} type - Loại thông báo (danger, success, warning, info)
     */
    function showAlert(message, type = 'danger') {
        // Tạo phần tử alert nếu không tồn tại
        let alertElement = document.getElementById('upload-alert');
        if (!alertElement) {
            alertElement = document.createElement('div');
            alertElement.id = 'upload-alert';
            alertElement.className = `alert alert-${type} mt-3`;
            alertElement.setAttribute('role', 'alert');
            uploadArea.parentNode.insertBefore(alertElement, uploadArea.nextSibling);
        } else {
            alertElement.className = `alert alert-${type} mt-3`;
        }
        
        alertElement.textContent = message;
        alertElement.style.display = 'block';
        
        // Tự động ẩn thông báo thành công sau 5 giây
        if (type === 'success') {
            setTimeout(() => {
                alertElement.style.display = 'none';
            }, 5000);
        }
    }
    
    /**
     * Đặt lại form tải lên
     */
    function resetUploadForm() {
        if (fileInput) fileInput.value = '';
        
        // Hiển thị lại placeholder
        if (uploadPlaceholder) uploadPlaceholder.classList.remove('d-none');
        
        // Ẩn phần tiến trình và hoàn thành
        if (uploadProgressContainer) uploadProgressContainer.classList.add('d-none');
        if (uploadComplete) uploadComplete.classList.add('d-none');
        
        // Reset tiến trình
        if (uploadProgressBar) uploadProgressBar.style.width = '0%';
        if (uploadStatus) uploadStatus.textContent = '0% hoàn thành';
    }
}); 