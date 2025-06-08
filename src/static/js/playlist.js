/**
 * playlist.js - Quản lý và hiển thị playlist
 */

let playlists = []; // Danh sách tất cả các playlist
let currentPlaylist = null; // Playlist hiện tại đang hiển thị
let availableTracks = []; // Danh sách bài hát có sẵn để thêm vào playlist
let selectedTracks = []; // Danh sách bài hát đã chọn để thêm vào playlist

document.addEventListener('DOMContentLoaded', function() {
    // Tải danh sách playlist
    loadPlaylists();
    
    // Thiết lập sự kiện cho các nút
    setupEventListeners();
});

/**
 * Tải danh sách playlist từ API
 */
function loadPlaylists() {
    fetch('/api/playlist/list')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                playlists = data.playlists;
                renderPlaylists();
                
                // Kiểm tra xem có ID playlist trong URL không
                const urlParams = new URLSearchParams(window.location.search);
                const playlistId = urlParams.get('id');
                
                if (playlistId) {
                    const playlist = playlists.find(p => p.id === playlistId);
                    if (playlist) {
                        loadPlaylist(playlist.id);
                    }
                }
            } else {
                showAlert('Không thể tải danh sách playlist: ' + (data.message || 'Lỗi không xác định'), 'danger');
            }
        })
        .catch(error => {
            console.error('Error loading playlists:', error);
            showAlert('Đã xảy ra lỗi khi tải danh sách playlist.', 'danger');
        });
}

/**
 * Hiển thị danh sách playlist
 */
function renderPlaylists() {
    const playlistContainer = document.getElementById('playlist-container');
    if (!playlistContainer) return;
    
    // Tạo HTML cho nút "Tạo playlist mới"
    let html = `
        <div class="col-md-3 col-sm-6 mb-4">
            <div class="playlist-card new-playlist-card h-100" data-bs-toggle="modal" data-bs-target="#createPlaylistModal">
                <i class="fa-solid fa-plus fa-2x mb-3"></i>
                <h5>Tạo playlist mới</h5>
            </div>
        </div>
    `;
    
    // Thêm các playlist hiện có
    playlists.forEach(playlist => {
        html += `
            <div class="col-md-3 col-sm-6 mb-4">
                <div class="playlist-card h-100">
                    <div class="playlist-card-img">
                        <i class="fa-solid fa-music"></i>
                        <div class="play-overlay">
                            <button class="play-btn" data-id="${playlist.id}" data-action="play">
                                <i class="fa-solid fa-play"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">${playlist.name}</h5>
                        <p class="card-text text-muted small">${playlist.track_count || 0} bài hát</p>
                        <a href="?id=${playlist.id}" class="stretched-link"></a>
                    </div>
                </div>
            </div>
        `;
    });
    
    playlistContainer.innerHTML = html;
    
    // Thêm sự kiện cho các nút play
    document.querySelectorAll('.play-btn[data-action="play"]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const playlistId = this.getAttribute('data-id');
            playPlaylist(playlistId);
        });
    });
}

/**
 * Tải thông tin chi tiết playlist
 * @param {string} playlistId ID của playlist
 */
function loadPlaylist(playlistId) {
    fetch(`/api/playlist/${playlistId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentPlaylist = data.playlist;
                renderPlaylistDetail();
            } else {
                showAlert('Không thể tải thông tin playlist: ' + (data.message || 'Lỗi không xác định'), 'danger');
            }
        })
        .catch(error => {
            console.error('Error loading playlist:', error);
            showAlert('Đã xảy ra lỗi khi tải thông tin playlist.', 'danger');
        });
}

/**
 * Hiển thị chi tiết playlist
 */
function renderPlaylistDetail() {
    if (!currentPlaylist) return;
    
    const playlistDetail = document.getElementById('playlist-detail');
    const playlistTitle = document.getElementById('playlist-title');
    const playlistTrackCount = document.getElementById('playlist-track-count');
    const playlistDuration = document.getElementById('playlist-duration');
    const playlistTracks = document.getElementById('playlist-tracks');
    
    if (!playlistDetail || !playlistTitle || !playlistTrackCount || !playlistDuration || !playlistTracks) return;
    
    // Hiển thị phần chi tiết playlist
    playlistDetail.classList.remove('d-none');
    
    // Cập nhật thông tin playlist
    playlistTitle.textContent = currentPlaylist.name;
    playlistTrackCount.textContent = `${currentPlaylist.tracks.length} bài hát`;
    
    // Tính tổng thời lượng
    const totalDuration = currentPlaylist.tracks.reduce((total, track) => total + (track.duration || 0), 0);
    playlistDuration.textContent = formatTime(totalDuration);
    
    // Hiển thị danh sách bài hát
    if (currentPlaylist.tracks.length === 0) {
        playlistTracks.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-5">
                    <div class="alert alert-info">
                        <i class="fa-solid fa-info-circle me-2"></i>
                        Playlist này chưa có bài hát nào.
                    </div>
                    <button class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#addTracksModal">
                        <i class="fa-solid fa-plus me-2"></i>Thêm bài hát
                    </button>
                </td>
            </tr>
        `;
    } else {
        let html = '';
        
        currentPlaylist.tracks.forEach((track, index) => {
            const statusClass = track.status === 'original' 
                ? 'bg-success' 
                : track.status === 'encrypted' 
                    ? 'bg-danger' 
                    : 'bg-info';
            
            const statusText = track.status === 'original' 
                ? 'Gốc' 
                : track.status === 'encrypted' 
                    ? 'Đã mã hóa' 
                    : 'Đã giải mã';
            
            html += `
                <tr class="track-item" data-id="${track.id}">
                    <td>
                        <span class="track-number">${index + 1}</span>
                        <button class="track-play-btn">
                            <i class="fa-solid fa-play"></i>
                        </button>
                    </td>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="track-info">
                                <div class="track-name">${track.name}</div>
                                <div class="track-meta">
                                    <span>${formatFileSize(track.size)}</span>
                                </div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="badge ${statusClass}">${statusText}</span>
                    </td>
                    <td>${formatTime(track.duration || 0)}</td>
                    <td>
                        <div class="track-actions">
                            <button class="track-action-btn action-button" data-action="remove-from-playlist" data-id="${track.id}" data-bs-toggle="tooltip" title="Xóa khỏi playlist">
                                <i class="fa-solid fa-minus-circle"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        playlistTracks.innerHTML = html;
        
        // Khởi tạo tooltips
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltips.forEach(tooltip => {
                new bootstrap.Tooltip(tooltip);
            });
        }
        
        // Gắn sự kiện cho các track
        setupTrackEvents();
    }
    
    // Tải danh sách bài hát có sẵn cho modal thêm bài hát
    loadAvailableTracks();
}

/**
 * Tải danh sách bài hát có sẵn để thêm vào playlist
 */
function loadAvailableTracks() {
    fetch('/audio/files')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Lọc ra các bài hát chưa có trong playlist hiện tại
                const currentTrackIds = currentPlaylist.tracks.map(track => track.id);
                availableTracks = data.audio_files.filter(track => !currentTrackIds.includes(track.id));
                
                // Hiển thị danh sách bài hát trong modal
                renderAvailableTracks();
            }
        })
        .catch(error => {
            console.error('Error loading available tracks:', error);
        });
}

/**
 * Hiển thị danh sách bài hát có sẵn trong modal
 */
function renderAvailableTracks() {
    const availableTracksElement = document.getElementById('available-tracks');
    if (!availableTracksElement) return;
    
    if (availableTracks.length === 0) {
        availableTracksElement.innerHTML = `
            <tr>
                <td colspan="4" class="text-center py-4">
                    <div class="alert alert-info">
                        <i class="fa-solid fa-info-circle me-2"></i>
                        Không có bài hát nào khả dụng để thêm.
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    
    availableTracks.forEach(track => {
        const statusClass = track.status === 'original' 
            ? 'bg-success' 
            : track.status === 'encrypted' 
                ? 'bg-danger' 
                : 'bg-info';
        
        const statusText = track.status === 'original' 
            ? 'Gốc' 
            : track.status === 'encrypted' 
                ? 'Đã mã hóa' 
                : 'Đã giải mã';
        
        const isSelected = selectedTracks.includes(track.id);
        
        html += `
            <tr>
                <td>
                    <div class="form-check">
                        <input class="form-check-input track-checkbox" type="checkbox" value="${track.id}" ${isSelected ? 'checked' : ''}>
                    </div>
                </td>
                <td>
                    <div class="track-name">${track.name}</div>
                </td>
                <td>
                    <span class="badge ${statusClass}">${statusText}</span>
                </td>
                <td>${formatTime(track.duration || 0)}</td>
            </tr>
        `;
    });
    
    availableTracksElement.innerHTML = html;
    
    // Gắn sự kiện cho các checkbox
    document.querySelectorAll('.track-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const trackId = this.value;
            
            if (this.checked) {
                if (!selectedTracks.includes(trackId)) {
                    selectedTracks.push(trackId);
                }
            } else {
                const index = selectedTracks.indexOf(trackId);
                if (index !== -1) {
                    selectedTracks.splice(index, 1);
                }
            }
        });
    });
}

/**
 * Gắn sự kiện cho các track trong playlist
 */
function setupTrackEvents() {
    // Sự kiện click vào track để phát nhạc
    document.querySelectorAll('.track-item').forEach(track => {
        track.addEventListener('click', function(e) {
            // Bỏ qua nếu click vào nút hành động
            if (e.target.closest('.action-button')) return;
            
            const trackId = this.getAttribute('data-id');
            const trackIndex = currentPlaylist.tracks.findIndex(t => t.id === trackId);
            
            if (trackIndex !== -1 && window.musicPlayer) {
                window.musicPlayer.playlist = currentPlaylist.tracks;
                window.musicPlayer.playTrack(trackIndex);
            }
        });
    });
    
    // Sự kiện xóa track khỏi playlist
    document.querySelectorAll('.action-button[data-action="remove-from-playlist"]').forEach(button => {
        button.addEventListener('click', function() {
            const trackId = this.getAttribute('data-id');
            removeTrackFromPlaylist(trackId);
        });
    });
}

/**
 * Thiết lập các sự kiện
 */
function setupEventListeners() {
    // Sự kiện nút tạo playlist
    const savePlaylistButton = document.getElementById('save-playlist');
    if (savePlaylistButton) {
        savePlaylistButton.addEventListener('click', createPlaylist);
    }
    
    // Sự kiện nút phát playlist
    const playPlaylistButton = document.getElementById('play-playlist');
    if (playPlaylistButton) {
        playPlaylistButton.addEventListener('click', function() {
            if (currentPlaylist && currentPlaylist.tracks.length > 0) {
                playPlaylist(currentPlaylist.id);
            } else {
                showAlert('Playlist này chưa có bài hát nào để phát.', 'warning');
            }
        });
    }
    
    // Sự kiện nút chỉnh sửa playlist
    const editPlaylistButton = document.getElementById('edit-playlist');
    if (editPlaylistButton) {
        editPlaylistButton.addEventListener('click', function() {
            // Hiện modal chỉnh sửa
            // TODO: Implement edit playlist
            showAlert('Tính năng chỉnh sửa playlist sẽ sớm được phát triển.', 'info');
        });
    }
    
    // Sự kiện nút xóa playlist
    const deletePlaylistButton = document.getElementById('delete-playlist');
    if (deletePlaylistButton) {
        deletePlaylistButton.addEventListener('click', function() {
            if (currentPlaylist) {
                if (confirm(`Bạn có chắc chắn muốn xóa playlist "${currentPlaylist.name}"?`)) {
                    deletePlaylist(currentPlaylist.id);
                }
            }
        });
    }
    
    // Sự kiện thêm bài hát đã chọn vào playlist
    const addSelectedTracksButton = document.getElementById('add-selected-tracks');
    if (addSelectedTracksButton) {
        addSelectedTracksButton.addEventListener('click', function() {
            if (selectedTracks.length === 0) {
                showAlert('Vui lòng chọn ít nhất một bài hát để thêm.', 'warning');
                return;
            }
            
            addTracksToPlaylist(currentPlaylist.id, selectedTracks);
        });
    }
    
    // Sự kiện tìm kiếm bài hát trong modal
    const trackSearchInput = document.getElementById('track-search');
    if (trackSearchInput) {
        trackSearchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            
            document.querySelectorAll('#available-tracks tr').forEach(row => {
                const trackName = row.querySelector('.track-name');
                if (!trackName) return;
                
                const name = trackName.textContent.toLowerCase();
                
                if (name.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
    
    // Reset selectedTracks khi modal được mở
    const addTracksModal = document.getElementById('addTracksModal');
    if (addTracksModal) {
        addTracksModal.addEventListener('show.bs.modal', function() {
            selectedTracks = [];
        });
    }
}

/**
 * Tạo playlist mới
 */
function createPlaylist() {
    const playlistNameInput = document.getElementById('playlist-name');
    const playlistDescriptionInput = document.getElementById('playlist-description');
    
    if (!playlistNameInput) return;
    
    const name = playlistNameInput.value.trim();
    const description = playlistDescriptionInput ? playlistDescriptionInput.value.trim() : '';
    
    if (!name) {
        showAlert('Vui lòng nhập tên cho playlist.', 'warning');
        return;
    }
    
    // Gửi request tạo playlist
    fetch('/api/playlist/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name,
            description
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Playlist đã được tạo thành công!', 'success');
            
            // Đóng modal
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('createPlaylistModal'));
                if (modal) {
                    modal.hide();
                }
            }
            
            // Reset form
            if (playlistNameInput) playlistNameInput.value = '';
            if (playlistDescriptionInput) playlistDescriptionInput.value = '';
            
            // Tải lại danh sách playlist
            loadPlaylists();
            
            // Chuyển đến trang chi tiết playlist mới
            if (data.playlist && data.playlist.id) {
                window.location.href = `?id=${data.playlist.id}`;
            }
        } else {
            showAlert('Không thể tạo playlist: ' + (data.message || 'Lỗi không xác định'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error creating playlist:', error);
        showAlert('Đã xảy ra lỗi khi tạo playlist.', 'danger');
    });
}

/**
 * Xóa playlist
 * @param {string} playlistId ID của playlist cần xóa
 */
function deletePlaylist(playlistId) {
    fetch(`/api/playlist/${playlistId}/delete`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Playlist đã được xóa thành công!', 'success');
            
            // Tải lại danh sách playlist
            loadPlaylists();
            
            // Ẩn phần chi tiết playlist
            const playlistDetail = document.getElementById('playlist-detail');
            if (playlistDetail) {
                playlistDetail.classList.add('d-none');
            }
            
            // Xóa tham số id khỏi URL
            window.history.replaceState({}, document.title, window.location.pathname);
            
            // Reset currentPlaylist
            currentPlaylist = null;
        } else {
            showAlert('Không thể xóa playlist: ' + (data.message || 'Lỗi không xác định'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error deleting playlist:', error);
        showAlert('Đã xảy ra lỗi khi xóa playlist.', 'danger');
    });
}

/**
 * Phát playlist
 * @param {string} playlistId ID của playlist cần phát
 */
function playPlaylist(playlistId) {
    const playlist = playlists.find(p => p.id === playlistId);
    if (!playlist) return;
    
    fetch(`/api/playlist/${playlistId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.playlist.tracks.length > 0) {
                if (window.musicPlayer) {
                    window.musicPlayer.playlist = data.playlist.tracks;
                    window.musicPlayer.playTrack(0);
                } else {
                    // Nếu không có player, chuyển đến trang playlist với ID
                    window.location.href = `?id=${playlistId}`;
                }
            } else {
                showAlert('Playlist này không có bài hát nào để phát.', 'warning');
            }
        })
        .catch(error => {
            console.error('Error playing playlist:', error);
            showAlert('Đã xảy ra lỗi khi phát playlist.', 'danger');
        });
}

/**
 * Thêm bài hát vào playlist
 * @param {string} playlistId ID của playlist
 * @param {Array} trackIds Danh sách ID của các bài hát cần thêm
 */
function addTracksToPlaylist(playlistId, trackIds) {
    if (!playlistId || !trackIds || trackIds.length === 0) return;
    
    fetch(`/api/playlist/${playlistId}/add_tracks`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            track_ids: trackIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Đã thêm bài hát vào playlist thành công!', 'success');
            
            // Đóng modal
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('addTracksModal'));
                if (modal) {
                    modal.hide();
                }
            }
            
            // Tải lại thông tin playlist
            loadPlaylist(playlistId);
            
            // Reset selectedTracks
            selectedTracks = [];
        } else {
            showAlert('Không thể thêm bài hát vào playlist: ' + (data.message || 'Lỗi không xác định'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error adding tracks to playlist:', error);
        showAlert('Đã xảy ra lỗi khi thêm bài hát vào playlist.', 'danger');
    });
}

/**
 * Xóa bài hát khỏi playlist
 * @param {string} trackId ID của bài hát cần xóa
 */
function removeTrackFromPlaylist(trackId) {
    if (!currentPlaylist || !trackId) return;
    
    fetch(`/api/playlist/${currentPlaylist.id}/remove_track`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            track_id: trackId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Đã xóa bài hát khỏi playlist thành công!', 'success');
            
            // Tải lại thông tin playlist
            loadPlaylist(currentPlaylist.id);
        } else {
            showAlert('Không thể xóa bài hát khỏi playlist: ' + (data.message || 'Lỗi không xác định'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error removing track from playlist:', error);
        showAlert('Đã xảy ra lỗi khi xóa bài hát khỏi playlist.', 'danger');
    });
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
 * Format thời gian dạng mm:ss
 * @param {number} seconds Số giây
 * @returns {string} Thời gian dạng mm:ss
 */
function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Hiển thị thông báo
 * @param {string} message Nội dung thông báo
 * @param {string} type Loại thông báo (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    // Kiểm tra xem hàm có tồn tại trong global scope không
    if (typeof window.showAlert === 'function') {
        window.showAlert(message, type);
    } else {
        // Fallback nếu không có hàm toàn cục
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
            setTimeout(() => {
                document.body.removeChild(alertContainer);
            }, 500);
        }, 3000);
    }
} 