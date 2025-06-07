/**
 * Quản lý thư viện âm thanh
 */

class AudioLibrary {
    constructor() {
        this.audioList = [];
        this.selectedFile = null;
        
        // DOM Elements
        this.audioListElement = document.getElementById('audio-list');
        this.filterInput = document.getElementById('filter-input');
        this.filterType = document.getElementById('filter-type');
        this.encryptButton = document.getElementById('encrypt-button');
        this.decryptButton = document.getElementById('decrypt-button');
        this.downloadButton = document.getElementById('download-button');
        this.noFileSelected = document.getElementById('no-file-selected');
        this.encryptionOptions = document.getElementById('encryption-options');
        this.selectedFileName = document.getElementById('selected-file-name');
        this.encryptSection = document.getElementById('encrypt-section');
        this.decryptSection = document.getElementById('decrypt-section');
        
        this.init();
    }
    
    init() {
        // Tải danh sách tệp âm thanh
        this.loadAudioFiles();
        
        // Sự kiện lọc
        if (this.filterInput) {
            this.filterInput.addEventListener('input', () => this.filterAudioList());
        }
        
        if (this.filterType) {
            this.filterType.addEventListener('change', () => this.filterAudioList());
        }
        
        // Sự kiện mã hóa
        if (this.encryptButton) {
            this.encryptButton.addEventListener('click', () => this.encryptAudio());
        }
        
        // Sự kiện giải mã
        if (this.decryptButton) {
            this.decryptButton.addEventListener('click', () => this.decryptAudio());
        }
        
        // Sự kiện tải xuống
        if (this.downloadButton) {
            this.downloadButton.addEventListener('click', () => this.downloadAudio());
        }
    }
    
    loadAudioFiles() {
        // Gửi yêu cầu API để lấy danh sách tệp âm thanh
        fetch('/audio/files')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.files) {
                    this.audioList = data.files;
                    this.renderAudioList(this.audioList);
                } else {
                    this.showError('Không thể tải danh sách tệp âm thanh');
                }
            })
            .catch(error => {
                console.error('Error loading audio files:', error);
                this.showError('Đã xảy ra lỗi khi tải danh sách tệp âm thanh');
            });
    }
    
    renderAudioList(files) {
        if (!this.audioListElement) return;
        
        if (files.length === 0) {
            this.audioListElement.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">
                        <p class="my-3">Không có tệp âm thanh nào. <a href="/audio/upload">Tải lên tệp mới</a>?</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        let html = '';
        files.forEach((file, index) => {
            const statusClass = file.status === 'encrypted' ? 'danger' : (file.status === 'decrypted' ? 'info' : 'success');
            const statusText = file.status === 'encrypted' ? 'Đã mã hóa' : (file.status === 'decrypted' ? 'Đã giải mã' : 'Gốc');
            
            html += `
                <tr class="audio-item" data-file-id="${file.id}">
                    <td>${index + 1}</td>
                    <td>${file.name}</td>
                    <td><span class="badge bg-${statusClass}">${statusText}</span></td>
                    <td>${this.formatDate(file.upload_date)}</td>
                    <td>
                        <button class="btn btn-sm play-button" data-file-id="${file.id}">
                            <i class="fa-solid fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-primary select-button" data-file-id="${file.id}">
                            <i class="fa-solid fa-check"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        this.audioListElement.innerHTML = html;
        
        // Thêm sự kiện cho các nút
        const playButtons = document.querySelectorAll('.play-button');
        playButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const fileId = button.getAttribute('data-file-id');
                this.playAudio(fileId);
            });
        });
        
        const selectButtons = document.querySelectorAll('.select-button');
        selectButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const fileId = button.getAttribute('data-file-id');
                this.selectFile(fileId);
            });
        });
        
        const rows = document.querySelectorAll('.audio-item');
        rows.forEach(row => {
            row.addEventListener('click', () => {
                const fileId = row.getAttribute('data-file-id');
                this.selectFile(fileId);
            });
        });
    }
    
    filterAudioList() {
        const query = this.filterInput.value.toLowerCase();
        const filterType = this.filterType.value;
        
        const filteredFiles = this.audioList.filter(file => {
            const nameMatch = file.name.toLowerCase().includes(query);
            const typeMatch = filterType === 'all' || file.status === filterType;
            return nameMatch && typeMatch;
        });
        
        this.renderAudioList(filteredFiles);
    }
    
    playAudio(fileId) {
        const file = this.audioList.find(f => f.id === fileId);
        if (!file) return;
        
        // Gửi yêu cầu API để lấy URL của tệp âm thanh
        fetch(`/audio/download/${fileId}/${file.status}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Không thể tải tệp âm thanh');
                }
                return response.blob();
            })
            .then(blob => {
                const audioUrl = URL.createObjectURL(blob);
                
                // Tạo thông tin bài hát
                const track = {
                    id: file.id,
                    name: file.name,
                    url: audioUrl,
                    status: file.status
                };
                
                // Gọi trình phát nhạc để phát
                if (window.musicPlayer) {
                    window.musicPlayer.setPlaylist([track]);
                    window.musicPlayer.play();
                }
            })
            .catch(error => {
                console.error('Error playing audio:', error);
                this.showError('Không thể phát tệp âm thanh');
            });
    }
    
    selectFile(fileId) {
        const file = this.audioList.find(f => f.id === fileId);
        if (!file) return;
        
        this.selectedFile = file;
        
        // Hiển thị tùy chọn mã hóa/giải mã
        if (this.noFileSelected) this.noFileSelected.classList.add('d-none');
        if (this.encryptionOptions) this.encryptionOptions.classList.remove('d-none');
        
        // Hiển thị tên tệp
        if (this.selectedFileName) this.selectedFileName.textContent = file.name;
        
        // Hiển thị tùy chọn mã hóa hoặc giải mã dựa trên trạng thái của tệp
        if (file.status === 'encrypted') {
            // Tệp đã mã hóa => hiển thị tùy chọn giải mã
            if (this.encryptSection) this.encryptSection.classList.add('d-none');
            if (this.decryptSection) this.decryptSection.classList.remove('d-none');
        } else {
            // Tệp chưa mã hóa => hiển thị tùy chọn mã hóa
            if (this.encryptSection) this.encryptSection.classList.remove('d-none');
            if (this.decryptSection) this.decryptSection.classList.add('d-none');
        }
    }
    
    encryptAudio() {
        if (!this.selectedFile) return;
        
        const algorithm = document.querySelector('input[name="algorithm"]:checked').value;
        
        // Hiển thị thông báo đang xử lý
        this.showMessage('Đang mã hóa tệp âm thanh...', 'info');
        
        // Gửi yêu cầu API để mã hóa tệp
        fetch(`/audio/encrypt/${this.selectedFile.id}/${algorithm}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showMessage('Mã hóa tệp thành công!', 'success');
                // Cập nhật danh sách tệp
                this.loadAudioFiles();
            } else {
                this.showError(data.error || 'Không thể mã hóa tệp âm thanh');
            }
        })
        .catch(error => {
            console.error('Error encrypting audio:', error);
            this.showError('Đã xảy ra lỗi khi mã hóa tệp âm thanh');
        });
    }
    
    decryptAudio() {
        if (!this.selectedFile) return;
        
        // Hiển thị thông báo đang xử lý
        this.showMessage('Đang giải mã tệp âm thanh...', 'info');
        
        // Gửi yêu cầu API để giải mã tệp
        fetch(`/audio/decrypt/${this.selectedFile.id}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showMessage('Giải mã tệp thành công!', 'success');
                // Cập nhật danh sách tệp
                this.loadAudioFiles();
            } else {
                this.showError(data.error || 'Không thể giải mã tệp âm thanh');
            }
        })
        .catch(error => {
            console.error('Error decrypting audio:', error);
            this.showError('Đã xảy ra lỗi khi giải mã tệp âm thanh');
        });
    }
    
    downloadAudio() {
        if (!this.selectedFile) return;
        
        // Xác định loại tệp để tải xuống (original, encrypted, decrypted)
        const fileType = this.selectedFile.status;
        
        // Mở cửa sổ tải xuống
        window.location.href = `/audio/download/${this.selectedFile.id}/${fileType}`;
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    showError(message) {
        console.error(message);
        // Hiển thị thông báo lỗi (có thể thêm vào giao diện)
    }
    
    showMessage(message, type = 'info') {
        console.log(message);
        // Hiển thị thông báo (có thể thêm vào giao diện)
    }
}

// Khởi tạo thư viện âm thanh khi DOM đã sẵn sàng
document.addEventListener('DOMContentLoaded', function() {
    const audioLibrary = new AudioLibrary();
}); 