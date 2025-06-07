/**
 * Quản lý trang phát nhạc riêng biệt
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const playerTitle = document.getElementById('player-title');
    const playerArtist = document.getElementById('player-artist');
    const playerStatus = document.getElementById('player-status');
    const playerArtwork = document.getElementById('player-artwork');
    const playPauseButton = document.getElementById('btn-play-pause');
    const playIcon = document.getElementById('play-icon');
    const prevButton = document.getElementById('btn-previous');
    const nextButton = document.getElementById('btn-next');
    const currentTimeEl = document.getElementById('time-current');
    const totalTimeEl = document.getElementById('time-total');
    const progressBar = document.getElementById('progress-bar');
    const progressCurrent = document.getElementById('progress-current');
    const volumeIcon = document.getElementById('volume-icon');
    const volumeSlider = document.getElementById('volume-slider');
    const volumeLevel = document.getElementById('volume-level');
    const visualization = document.getElementById('visualization');
    const libraryButton = document.getElementById('btn-library');
    const encryptButton = document.getElementById('btn-encrypt-decrypt');
    
    // Âm thanh
    const audio = new Audio();
    let isPlaying = false;
    let currentTrack = null;
    let playlist = [];
    let currentTrackIndex = -1;
    let volume = 0.8;
    
    // Lấy tham số từ URL
    const urlParams = new URLSearchParams(window.location.search);
    const trackId = urlParams.get('track');
    
    // Khởi tạo
    init();
    
    function init() {
        // Thiết lập sự kiện
        setupEventListeners();
        
        // Tải danh sách nhạc
        loadPlaylist();
        
        // Thiết lập âm lượng ban đầu
        audio.volume = volume;
        updateVolumeUI();
        
        // Nếu có trackId trong URL, phát bài hát đó
        if (trackId) {
            loadAndPlayTrack(trackId);
        }
    }
    
    function setupEventListeners() {
        // Nút phát/tạm dừng
        if (playPauseButton) {
            playPauseButton.addEventListener('click', togglePlay);
        }
        
        // Nút trước/sau
        if (prevButton) {
            prevButton.addEventListener('click', playPrevious);
        }
        
        if (nextButton) {
            nextButton.addEventListener('click', playNext);
        }
        
        // Sự kiện audio
        audio.addEventListener('timeupdate', updateProgress);
        audio.addEventListener('loadedmetadata', updateTotalTime);
        audio.addEventListener('ended', handleTrackEnd);
        audio.addEventListener('play', () => {
            isPlaying = true;
            updatePlayPauseUI();
            visualization.classList.add('playing');
        });
        audio.addEventListener('pause', () => {
            isPlaying = false;
            updatePlayPauseUI();
            visualization.classList.remove('playing');
        });
        
        // Thanh tiến độ
        if (progressBar) {
            progressBar.addEventListener('click', seekTrack);
        }
        
        // Âm lượng
        if (volumeIcon) {
            volumeIcon.addEventListener('click', toggleMute);
        }
        
        if (volumeSlider) {
            volumeSlider.addEventListener('click', changeVolume);
        }
        
        // Nút điều hướng
        if (libraryButton) {
            libraryButton.addEventListener('click', () => {
                window.location.href = '/audio/library';
            });
        }
        
        if (encryptButton) {
            encryptButton.addEventListener('click', () => {
                if (currentTrack) {
                    window.location.href = `/audio/library?select=${currentTrack.id}`;
                } else {
                    window.location.href = '/audio/library';
                }
            });
        }
        
        // Phím tắt
        document.addEventListener('keydown', handleKeyboard);
    }
    
    function loadPlaylist() {
        // Tải danh sách nhạc từ API
        fetch('/audio/files')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.files && data.files.length > 0) {
                    playlist = data.files;
                    
                    // Nếu không có trackId trong URL, chọn bài đầu tiên
                    if (!trackId && playlist.length > 0) {
                        currentTrackIndex = 0;
                        currentTrack = playlist[0];
                        updateTrackInfo();
                    }
                }
            })
            .catch(error => {
                console.error('Error loading playlist:', error);
            });
    }
    
    function loadAndPlayTrack(id) {
        // Tìm bài hát trong playlist
        const trackIndex = playlist.findIndex(track => track.id === id);
        
        if (trackIndex !== -1) {
            currentTrackIndex = trackIndex;
            currentTrack = playlist[trackIndex];
            playCurrentTrack();
        } else {
            // Nếu không tìm thấy trong playlist, tải thông tin bài hát từ API
            fetch(`/audio/track/${id}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.track) {
                        currentTrack = data.track;
                        // Tìm vị trí trong playlist
                        const index = playlist.findIndex(track => track.id === id);
                        if (index !== -1) {
                            currentTrackIndex = index;
                        }
                        playCurrentTrack();
                    }
                })
                .catch(error => {
                    console.error('Error loading track:', error);
                });
        }
    }
    
    function playCurrentTrack() {
        if (!currentTrack) return;
        
        // Cập nhật thông tin bài hát
        updateTrackInfo();
        
        // Tải và phát nhạc
        audio.src = `/audio/stream/${currentTrack.id}`;
        audio.load();
        audio.play()
            .catch(error => {
                console.error('Error playing audio:', error);
            });
    }
    
    function togglePlay() {
        if (!currentTrack) {
            if (playlist.length > 0) {
                currentTrackIndex = 0;
                currentTrack = playlist[0];
                playCurrentTrack();
            }
            return;
        }
        
        if (isPlaying) {
            audio.pause();
        } else {
            audio.play()
                .catch(error => {
                    console.error('Error playing audio:', error);
                });
        }
    }
    
    function playNext() {
        if (playlist.length === 0) return;
        
        currentTrackIndex = (currentTrackIndex + 1) % playlist.length;
        currentTrack = playlist[currentTrackIndex];
        playCurrentTrack();
    }
    
    function playPrevious() {
        if (playlist.length === 0) return;
        
        // Nếu đang phát hơn 3 giây, quay về đầu bài
        if (audio.currentTime > 3) {
            audio.currentTime = 0;
            return;
        }
        
        currentTrackIndex = (currentTrackIndex - 1 + playlist.length) % playlist.length;
        currentTrack = playlist[currentTrackIndex];
        playCurrentTrack();
    }
    
    function seekTrack(e) {
        if (!audio.duration) return;
        
        const rect = progressBar.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        audio.currentTime = percent * audio.duration;
    }
    
    function updateProgress() {
        if (!audio.duration) return;
        
        const percent = (audio.currentTime / audio.duration) * 100;
        progressCurrent.style.width = `${percent}%`;
        
        currentTimeEl.textContent = formatTime(audio.currentTime);
    }
    
    function updateTotalTime() {
        totalTimeEl.textContent = formatTime(audio.duration);
    }
    
    function handleTrackEnd() {
        playNext();
    }
    
    function toggleMute() {
        if (audio.volume > 0) {
            audio.volume = 0;
        } else {
            audio.volume = volume;
        }
        
        updateVolumeUI();
    }
    
    function changeVolume(e) {
        const rect = volumeSlider.getBoundingClientRect();
        volume = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        audio.volume = volume;
        
        updateVolumeUI();
    }
    
    function updateVolumeUI() {
        volumeLevel.style.width = `${audio.volume * 100}%`;
        
        // Cập nhật icon
        const volumeIconElement = volumeIcon.querySelector('i');
        if (audio.volume === 0) {
            volumeIconElement.className = 'fa-solid fa-volume-xmark';
        } else if (audio.volume < 0.5) {
            volumeIconElement.className = 'fa-solid fa-volume-low';
        } else {
            volumeIconElement.className = 'fa-solid fa-volume-high';
        }
    }
    
    function updateTrackInfo() {
        if (!currentTrack) return;
        
        playerTitle.textContent = currentTrack.name || 'Không xác định';
        playerArtist.textContent = currentTrack.artist || 'Chưa có thông tin';
        
        // Cập nhật trạng thái
        playerStatus.textContent = currentTrack.status === 'encrypted' 
            ? 'Đã mã hóa' 
            : currentTrack.status === 'decrypted' 
                ? 'Đã giải mã' 
                : 'Gốc';
        
        // Cập nhật class
        playerStatus.className = 'player-status';
        playerStatus.classList.add(currentTrack.status);
    }
    
    function updatePlayPauseUI() {
        if (isPlaying) {
            playIcon.className = 'fa-solid fa-pause';
        } else {
            playIcon.className = 'fa-solid fa-play';
        }
    }
    
    function handleKeyboard(e) {
        // Bỏ qua nếu đang nhập vào input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        switch (e.key) {
            case ' ': // Space - Phát/tạm dừng
                e.preventDefault();
                togglePlay();
                break;
            case 'ArrowLeft': // Mũi tên trái - Lùi 5 giây
                e.preventDefault();
                if (audio.currentTime) {
                    audio.currentTime = Math.max(0, audio.currentTime - 5);
                }
                break;
            case 'ArrowRight': // Mũi tên phải - Tiến 5 giây
                e.preventDefault();
                if (audio.duration) {
                    audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
                }
                break;
            case 'ArrowUp': // Mũi tên lên - Tăng âm lượng
                e.preventDefault();
                volume = Math.min(1, audio.volume + 0.05);
                audio.volume = volume;
                updateVolumeUI();
                break;
            case 'ArrowDown': // Mũi tên xuống - Giảm âm lượng
                e.preventDefault();
                volume = Math.max(0, audio.volume - 0.05);
                audio.volume = volume;
                updateVolumeUI();
                break;
            case 'n': // N - Bài kế tiếp
                playNext();
                break;
            case 'p': // P - Bài trước đó
                playPrevious();
                break;
            case 'm': // M - Tắt/bật âm lượng
                toggleMute();
                break;
        }
    }
    
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return '00:00';
        
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}); 