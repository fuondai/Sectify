/**
 * Trình phát nhạc Sectify
 * Xử lý phát nhạc, mã hóa và giải mã âm thanh
 */

// Đảm bảo chỉ khai báo 1 lần class MusicPlayer
if (typeof window.MusicPlayer === 'undefined') {
    class MusicPlayer {
        constructor() {
            // Phần tử DOM
            this.audioElement = new Audio();
            this.playButton = document.getElementById('play-button');
            this.prevButton = document.getElementById('prev-button');
            this.nextButton = document.getElementById('next-button');
            this.progressBar = document.getElementById('progress-bar');
            this.currentTimeElement = document.getElementById('current-time');
            this.durationElement = document.getElementById('duration');
            this.volumeControl = document.getElementById('volume-control');
            this.volumeButton = document.getElementById('volume-button');
            this.currentTrackInfo = document.getElementById('current-track-info');
            this.currentTrackName = document.getElementById('current-track-name');
            this.currentTrackStatus = document.getElementById('current-track-status');
            
            // Trạng thái
            this.playlist = [];
            this.currentTrackIndex = -1;
            this.isPlaying = false;
            this.volume = 0.8;
            this.previousVolume = 0.8;
            this.lastUpdateTime = 0;
            
            // Khởi tạo trình phát
            this.init();
        }
        
        /**
         * Khởi tạo trình phát và gắn các sự kiện
         */
        init() {
            // Thiết lập âm lượng ban đầu
            this.audioElement.volume = this.volume;
            
            // Sự kiện phát/tạm dừng
            this.playButton.addEventListener('click', () => this.togglePlay());
            
            // Sự kiện tiến/lùi bài
            this.prevButton.addEventListener('click', () => this.playPrevious());
            this.nextButton.addEventListener('click', () => this.playNext());
            
            // Sự kiện điều khiển âm lượng
            this.volumeControl.addEventListener('input', (e) => {
                this.setVolume(e.target.value / 100);
            });
            
            this.volumeButton.addEventListener('click', () => this.toggleMute());
            
            // Sự kiện thanh tiến độ
            this.progressBar.addEventListener('input', (e) => {
                const seekTime = (e.target.value / 100) * this.audioElement.duration;
                this.audioElement.currentTime = seekTime;
            });
            
            // Sự kiện audio
            this.audioElement.addEventListener('timeupdate', () => this.updateProgress());
            this.audioElement.addEventListener('ended', () => this.handleTrackEnd());
            this.audioElement.addEventListener('play', () => this.updatePlayButton(true));
            this.audioElement.addEventListener('pause', () => this.updatePlayButton(false));
            this.audioElement.addEventListener('loadedmetadata', () => {
                this.durationElement.textContent = this.formatTime(this.audioElement.duration);
                this.progressBar.disabled = false;
            });
            
            // Sự kiện phím
            document.addEventListener('keydown', (e) => this.handleKeyboardEvents(e));
            
            // Tải danh sách phát nếu có
            this.loadPlaylist();
        }
        
        /**
         * Tải danh sách phát từ API
         */
        loadPlaylist() {
            fetch('/audio/files')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Đảm bảo lấy đúng key trả về từ API backend
                        this.playlist = data.files || [];
                        
                        // Kiểm tra xem có bài hát nào được yêu cầu phát ngay không
                        const urlParams = new URLSearchParams(window.location.search);
                        const playTrackId = urlParams.get('play');
                        
                        if (playTrackId) {
                            const trackIndex = this.playlist.findIndex(track => track.id === playTrackId);
                            if (trackIndex !== -1) {
                                this.playTrack(trackIndex);
                            }
                        }
                        
                        // Kích hoạt các nút điều khiển nếu có playlist
                        if (Array.isArray(this.playlist) && this.playlist.length > 0) {
                            this.prevButton.disabled = false;
                            this.nextButton.disabled = false;
                            this.playButton.disabled = false;
                        }
                    }
                })
                .catch(error => console.error('Error loading playlist:', error));
        }
        
        /**
         * Phát/tạm dừng bài hiện tại
         */
        togglePlay() {
            if (this.currentTrackIndex === -1 && this.playlist.length > 0) {
                // Nếu chưa chọn bài nào, phát bài đầu tiên
                this.playTrack(0);
            } else {
                if (this.audioElement.paused) {
                    this.audioElement.play();
                } else {
                    this.audioElement.pause();
                }
            }
        }
        
        /**
         * Phát bài được chỉ định
         * @param {number} index Chỉ số bài hát trong playlist
         */
        playTrack(index) {
            if (index < 0 || index >= this.playlist.length) return;
            
            this.currentTrackIndex = index;
            const track = this.playlist[index];
            
            // Cập nhật nguồn audio
            this.audioElement.src = `/audio/stream/${track.id}`;
            this.audioElement.load();
            this.audioElement.play();
            
            // Cập nhật giao diện
            this.updateTrackInfo(track);
            
            // Cập nhật active track trong danh sách
            this.updateActiveTrack();
        }
        
        /**
         * Phát bài tiếp theo
         */
        playNext() {
            if (this.playlist.length === 0) return;
            
            let nextIndex = this.currentTrackIndex + 1;
            if (nextIndex >= this.playlist.length) {
                nextIndex = 0; // Quay về bài đầu tiên
            }
            
            this.playTrack(nextIndex);
        }
        
        /**
         * Phát bài trước đó
         */
        playPrevious() {
            if (this.playlist.length === 0) return;
            
            // Nếu đã phát quá 3 giây, quay về đầu bài hiện tại
            if (this.audioElement.currentTime > 3) {
                this.audioElement.currentTime = 0;
                return;
            }
            
            let prevIndex = this.currentTrackIndex - 1;
            if (prevIndex < 0) {
                prevIndex = this.playlist.length - 1; // Đi đến bài cuối cùng
            }
            
            this.playTrack(prevIndex);
        }
        
        /**
         * Cập nhật thanh tiến độ
         */
        updateProgress() {
            // Giới hạn tần suất cập nhật để tránh quá tải
            const now = Date.now();
            if (now - this.lastUpdateTime < 250) return;
            this.lastUpdateTime = now;
            
            const currentTime = this.audioElement.currentTime;
            const duration = this.audioElement.duration || 0;
            
            // Cập nhật thanh tiến độ
            if (!isNaN(duration) && duration > 0) {
                this.progressBar.value = (currentTime / duration) * 100;
            } else {
                this.progressBar.value = 0;
            }
            
            // Cập nhật thời gian
            this.currentTimeElement.textContent = this.formatTime(currentTime);
        }
        
        /**
         * Xử lý khi bài hát kết thúc
         */
        handleTrackEnd() {
            // Tự động phát bài tiếp theo
            this.playNext();
        }
        
        /**
         * Cập nhật thông tin bài hát
         * @param {Object} track Thông tin bài hát
         */
        updateTrackInfo(track) {
            // Hiển thị thông tin bài hát
            this.currentTrackInfo.classList.remove('d-none');
            this.currentTrackName.textContent = track.name;
            
            // Hiển thị trạng thái bài hát
            let statusText = 'Gốc';
            if (track.status === 'encrypted') {
                statusText = 'Đã mã hóa';
            } else if (track.status === 'decrypted') {
                statusText = 'Đã giải mã';
            }
            
            this.currentTrackStatus.textContent = statusText;
            
            // Cập nhật tiêu đề trang
            document.title = `${track.name} - Sectify`;
        }
        
        /**
         * Cập nhật nút phát/tạm dừng
         * @param {boolean} isPlaying Trạng thái phát
         */
        updatePlayButton(isPlaying) {
            this.isPlaying = isPlaying;
            
            if (isPlaying) {
                this.playButton.innerHTML = '<i class="fa-solid fa-pause"></i>';
            } else {
                this.playButton.innerHTML = '<i class="fa-solid fa-play"></i>';
            }
        }
        
        /**
         * Cập nhật bài hiện tại trong danh sách
         */
        updateActiveTrack() {
            // Xóa active class khỏi tất cả các track
            document.querySelectorAll('.track-item').forEach(el => {
                el.classList.remove('active');
            });
            
            if (this.currentTrackIndex !== -1) {
                const currentTrack = this.playlist[this.currentTrackIndex];
                const trackElement = document.querySelector(`.track-item[data-id="${currentTrack.id}"]`);
                
                if (trackElement) {
                    trackElement.classList.add('active');
                    // Cuộn đến bài hát hiện tại
                    trackElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        }
        
        /**
         * Thiết lập âm lượng
         * @param {number} value Giá trị âm lượng (0-1)
         */
        setVolume(value) {
            this.volume = value;
            this.audioElement.volume = value;
            this.volumeControl.value = value * 100;
            
            // Cập nhật icon âm lượng
            this.updateVolumeIcon();
            
            // Lưu âm lượng vào localStorage
            localStorage.setItem('sectifyVolume', value);
        }
        
        /**
         * Bật/tắt âm lượng
         */
        toggleMute() {
            if (this.audioElement.volume > 0) {
                this.previousVolume = this.audioElement.volume;
                this.setVolume(0);
            } else {
                this.setVolume(this.previousVolume);
            }
        }
        
        /**
         * Cập nhật icon âm lượng
         */
        updateVolumeIcon() {
            const volume = this.audioElement.volume;
            let iconClass = '';
            
            if (volume === 0) {
                iconClass = 'fa-volume-xmark';
            } else if (volume < 0.5) {
                iconClass = 'fa-volume-low';
            } else {
                iconClass = 'fa-volume-high';
            }
            
            this.volumeButton.innerHTML = `<i class="fa-solid ${iconClass}"></i>`;
        }
        
        /**
         * Xử lý sự kiện bàn phím
         * @param {KeyboardEvent} e Sự kiện bàn phím
         */
        handleKeyboardEvents(e) {
            // Chỉ xử lý khi không nhập vào input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            
            switch (e.key) {
                case ' ': // Space - Phát/tạm dừng
                    e.preventDefault();
                    this.togglePlay();
                    break;
                case 'ArrowLeft': // Mũi tên trái - Lùi 5 giây
                    e.preventDefault();
                    this.audioElement.currentTime = Math.max(0, this.audioElement.currentTime - 5);
                    break;
                case 'ArrowRight': // Mũi tên phải - Tiến 5 giây
                    e.preventDefault();
                    this.audioElement.currentTime = Math.min(this.audioElement.duration, this.audioElement.currentTime + 5);
                    break;
                case 'ArrowUp': // Mũi tên lên - Tăng âm lượng
                    e.preventDefault();
                    this.setVolume(Math.min(1, this.volume + 0.05));
                    break;
                case 'ArrowDown': // Mũi tên xuống - Giảm âm lượng
                    e.preventDefault();
                    this.setVolume(Math.max(0, this.volume - 0.05));
                    break;
                case 'n': // N - Bài kế tiếp
                    this.playNext();
                    break;
                case 'p': // P - Bài trước đó
                    this.playPrevious();
                    break;
                case 'm': // M - Tắt/bật âm lượng
                    this.toggleMute();
                    break;
            }
        }
        
        /**
         * Format thời gian dạng mm:ss
         * @param {number} seconds Số giây
         * @returns {string} Thời gian dạng mm:ss
         */
        formatTime(seconds) {
            if (isNaN(seconds) || seconds < 0) return '00:00';
            
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Thiết lập playlist mới
        setPlaylist(tracks) {
            this.playlist = tracks;
            this.currentTrackIndex = 0;
        }
    }
    window.MusicPlayer = MusicPlayer;
}

// Khởi tạo player khi trang đã load
document.addEventListener('DOMContentLoaded', function() {
    // Chỉ khởi tạo nếu trang có các phần tử của trình phát
    if (document.getElementById('play-button')) {
        window.musicPlayer = new MusicPlayer();
    }
    
    // Khởi tạo xử lý sự kiện cho các track trong thư viện
    initLibraryEvents();
});

/**
 * Khởi tạo sự kiện cho thư viện nhạc
 */
function initLibraryEvents() {
    // Xử lý click vào hàng trong bảng tracks
    const audioList = document.getElementById('audio-list');
    if (audioList) {
        audioList.addEventListener('click', function(e) {
            // Tìm hàng gần nhất
            const row = e.target.closest('tr');
            if (!row) return;
            
            // Kiểm tra xem có phải là nút hành động không
            if (e.target.closest('.action-button')) return;
            
            // Lấy ID track
            const trackId = row.getAttribute('data-id');
            
            // Tìm chỉ số trong playlist
            const trackIndex = window.musicPlayer.playlist.findIndex(track => track.id === trackId);
            
            if (trackIndex !== -1) {
                window.musicPlayer.playTrack(trackIndex);
            }
        });
    }
    
    // Xử lý nút stop (nếu có)
    const stopButton = document.getElementById('stop-button');
    if (stopButton) {
        stopButton.addEventListener('click', () => {
            if (window.musicPlayer) {
                window.musicPlayer.audioElement.pause();
                window.musicPlayer.audioElement.currentTime = 0;
                window.musicPlayer.updatePlayButton(false);
            }
        });
    }
    
    // Xử lý nút giải mã
    const decryptButton = document.getElementById('decrypt-button');
    if (decryptButton) {
        decryptButton.addEventListener('click', function() {
            const fileNameElement = document.getElementById('selected-file-name');
            if (!fileNameElement) return;
            
            const fileName = fileNameElement.textContent;
            
            // Hiển thị loading
            decryptButton.disabled = true;
            decryptButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Đang giải mã...';
            
            // Gọi API giải mã
            fetch('/audio/decrypt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_name: fileName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Giải mã thành công!', 'success');
                    // Tải lại danh sách nhạc
                    location.reload();
                } else {
                    showAlert(`Lỗi giải mã: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error decrypting:', error);
                showAlert('Đã xảy ra lỗi khi giải mã file.', 'danger');
            })
            .finally(() => {
                decryptButton.disabled = false;
                decryptButton.innerHTML = '<i class="fa-solid fa-unlock me-1"></i>Giải mã bài hát';
            });
        });
    }
    
    // Xử lý nút tải xuống
    const downloadButton = document.getElementById('download-button');
    if (downloadButton) {
        downloadButton.addEventListener('click', function() {
            const fileNameElement = document.getElementById('selected-file-name');
            if (!fileNameElement) return;
            
            const fileName = fileNameElement.textContent;
            const fileId = document.querySelector('#encryption-options').getAttribute('data-id');
            
            // Tạo link tải xuống
            const downloadUrl = `/api/audio/download/${fileId}`;
            
            // Tạo phần tử a và trigger click
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });
    }
    
    // Sự kiện chọn radio algorithm
    const algorithmRadios = document.querySelectorAll('input[name="algorithm"]');
    if (algorithmRadios.length > 0) {
        algorithmRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                // Xóa active class khỏi tất cả
                document.querySelectorAll('.method-option').forEach(el => {
                    el.classList.remove('active');
                });
                
                // Thêm active class vào option được chọn
                const methodOption = this.closest('.method-option');
                if (methodOption) {
                    methodOption.classList.add('active');
                }
            });
        });
    }
}

/**
 * Hiển thị thông báo
 * @param {string} message Nội dung thông báo
 * @param {string} type Loại thông báo (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alertContainer.style.zIndex = '9999';
    alertContainer.role = 'alert';
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(alertContainer);
    setTimeout(() => {
        alertContainer.classList.add('fade');
        setTimeout(() => document.body.removeChild(alertContainer), 500);
    }, 3000);
}