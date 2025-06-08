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
        
        // Sự kiện phát tất cả
        const playAllBtn = document.getElementById('play-all');
        if (playAllBtn) {
            playAllBtn.addEventListener('click', () => {
                if (this.audioList && this.audioList.length > 0) {
                    this.playAudio(this.audioList[0].id);
                }
            });
        }
        
        // Sự kiện mã hóa (dùng onclick để tránh bind nhiều lần)
        if (this.encryptButton) {
            this.encryptButton.onclick = () => this.encryptAudio();
        }
        
        // Sự kiện giải mã (dùng onclick để tránh bind nhiều lần)
        if (this.decryptButton) {
            this.decryptButton.onclick = () => this.decryptAudio();
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
        // Thêm nút xóa cho mỗi file
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
                        <button class="btn btn-sm play-button me-1" data-file-id="${file.id}">
                            <i class="fa-solid fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-button" data-file-id="${file.id}">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-primary select-button ms-1" data-file-id="${file.id}">
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
        
        // Đăng ký sự kiện xóa
        document.querySelectorAll('.delete-button').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                const id = btn.getAttribute('data-file-id');
                fetch(`/audio/delete/${id}`, { method: 'DELETE' })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) this.loadAudioFiles();
                        else this.showError(data.error);
                    });
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
        // Nếu file đang ở trạng thái mã hóa, luôn phát bản đã giải mã (nếu có)
        let playStatus = file.status === 'encrypted' ? 'decrypted' : file.status;
        fetch(`/audio/download/${fileId}/${playStatus}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Không thể tải tệp âm thanh');
                }
                return response.blob();
            })
            .then(blob => {
                const audioUrl = URL.createObjectURL(blob);
                const track = {
                    id: file.id,
                    name: file.name,
                    url: audioUrl,
                    status: file.status
                };
                if (window.musicPlayer) {
                    // Thiết lập playlist đầy đủ để prev/next hoạt động
                    const tracks = this.audioList.map(f => ({ id: f.id, name: f.name, status: f.status }));
                    window.musicPlayer.setPlaylist(tracks);
                    // Tìm chỉ số track hiện tại và phát
                    const idx = tracks.findIndex(t => t.id === file.id);
                    if (idx !== -1) window.musicPlayer.playTrack(idx);
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
        
        // Hiển thị đúng section theo trạng thái
        if (file.status === 'encrypted') {
            this.encryptSection.classList.add('d-none');
            this.decryptSection.classList.remove('d-none');
            this.downloadButton.disabled = false;
            this.decryptButton.disabled = false;
            this.encryptButton.disabled = true;
        } else if (file.status === 'decrypted') {
            this.encryptSection.classList.add('d-none');
            this.decryptSection.classList.add('d-none');
            this.downloadButton.disabled = false;
            this.decryptButton.disabled = true;
            this.encryptButton.disabled = true;
        } else {
            // original
            this.encryptSection.classList.remove('d-none');
            this.decryptSection.classList.add('d-none');
            this.downloadButton.disabled = false;
            this.decryptButton.disabled = true;
            this.encryptButton.disabled = false;
            if (this.encryptSection) this.encryptSection.classList.remove('d-none');
            if (this.decryptSection) this.decryptSection.classList.add('d-none');
        }
    }
    
    encryptAudio() {
        if (!this.selectedFile) return;
        const algorithm = document.querySelector('input[name="algorithm"]:checked').value;
        // Mẫu key AES 16 ký tự
        let encryptionKey = prompt('Nhập khóa mã hóa (16/24/32 ký tự). Ví dụ: 1234567890abcdef', '1234567890abcdef');
        this.encryptButton.blur();
        if (!encryptionKey) {
            this.showError('Bạn phải nhập khóa mã hóa!');
            return;
        }
        this.showMessage('Đang mã hóa tệp âm thanh...', 'info');
        fetch(`/audio/encrypt/${this.selectedFile.id}/${algorithm}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `encryption_key=${encodeURIComponent(encryptionKey)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showMessage('Mã hóa tệp thành công!', 'success');
                this.loadAudioFiles();
                setTimeout(() => {
                    if (this.selectedFile && this.selectedFile.status === 'encrypted') {
                        this.selectFile(this.selectedFile.id);
                    }
                }, 500);
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
        // Nhắc nhập key giống với key đã dùng mã hóa
        const decryptionKey = prompt('Nhập khóa giải mã (giống key mã hóa). Ví dụ: 1234567890abcdef', '1234567890abcdef');
        this.decryptButton.blur();
        if (!decryptionKey) {
            this.showError('Bạn phải nhập khóa giải mã!');
            return;
        }
        this.showMessage('Đang giải mã tệp âm thanh...', 'info');
        fetch(`/audio/decrypt/${this.selectedFile.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `decryption_key=${encodeURIComponent(decryptionKey)}`
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showMessage('Giải mã tệp thành công!', 'success');
                    // Reload danh sách và chọn lại file rồi tự động tải
                    this.loadAudioFiles();
                    setTimeout(() => {
                        if (this.selectedFile && this.selectedFile.status === 'decrypted') {
                            this.selectFile(this.selectedFile.id);
                            this.downloadAudio();
                        }
                    }, 500);
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
        if (typeof showAlert === 'function') {
            showAlert(message, 'danger');
        } else {
            alert(message);
        }
    }
    
    showMessage(message, type = 'info') {
        console.log(message);
        if (typeof showAlert === 'function') {
            showAlert(message, type);
        } else {
            alert(message);
        }
    }
}

// Khởi tạo audio library và music player khi DOM sẵn sàng
document.addEventListener('DOMContentLoaded', () => {
    const audioLib = new AudioLibrary();
    audioLib.init();
    // Nếu MusicPlayer đã được định nghĩa, khởi tạo duy nhất và gán global
    if (typeof MusicPlayer === 'function' && !window.musicPlayer) {
        window.musicPlayer = new MusicPlayer();
    }
});