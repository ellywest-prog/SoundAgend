// ── State ──────────────────────────────────
let currentPlatform = 'youtube';
let currentCountry = 'TR';
let currentPlayingCard = null;
let isPlaying = false;
let ytProgressInterval = null;
let currentTrackDuration = 0;
let currentTrackTime = 0;

const audioPlayer = document.getElementById('audio-player');
const ytIframe = document.getElementById('yt-player');

const platformColors = {
    youtube: '#ff0000',
    spotify: '#1db954',
    deezer: '#a238ff',
    apple: '#fc3c44',
};

// ── Platform Switching ────────────────────
document.querySelectorAll('.platform-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentPlatform = btn.dataset.platform;

        // Update accent color
        document.documentElement.style.setProperty('--accent-color', platformColors[currentPlatform]);

        // Update background glow
        const glow = document.querySelector('.background-glow');
        const color = platformColors[currentPlatform];
        glow.style.background = `radial-gradient(circle, ${color}20 0%, transparent 70%)`;

        fetchTracks();
    });
});

// ── Data Fetching ─────────────────────────
async function fetchTracks() {
    const topList = document.getElementById('top-tracks-list');
    const newList = document.getElementById('new-tracks-list');

    topList.innerHTML = '<div class="loading-shimmer">Yükleniyor...</div>';
    newList.innerHTML = '<div class="loading-shimmer">Yükleniyor...</div>';

    try {
        const [topRes, newRes] = await Promise.all([
            fetch(`/api/${currentPlatform}/top?country=${currentCountry}`),
            fetch(`/api/${currentPlatform}/new?country=${currentCountry}`)
        ]);

        const topTracks = await topRes.json();
        const newTracks = await newRes.json();

        renderTracks('top-tracks-list', topTracks);
        renderTracks('new-tracks-list', newTracks);
    } catch (error) {
        console.error('Veri çekme hatası:', error);
        topList.innerHTML = '<div class="error">Veri yüklenemedi. Sunucu çalışıyor mu?</div>';
        newList.innerHTML = '<div class="error">Veri yüklenemedi. Sunucu çalışıyor mu?</div>';
    }
}

// ── Track Rendering ───────────────────────
function renderTracks(elementId, tracks) {
    const list = document.getElementById(elementId);
    list.innerHTML = '';

    if (!tracks || tracks.length === 0) {
        list.innerHTML = '<div class="error">Gösterilecek parça bulunamadı.</div>';
        return;
    }

    tracks.forEach((track, index) => {
        const card = document.createElement('div');
        card.className = 'track-card';
        card.style.animationDelay = `${index * 0.08}s`;

        const thumbUrl = track.thumbnail || 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="56" height="56"><rect fill="%23222" width="56" height="56"/><text x="28" y="32" text-anchor="middle" fill="%23555" font-size="24">♪</text></svg>';

        const trackFullName = `${track.artist || ''} - ${track.title || ''}`;

        card.innerHTML = `
            <div class="track-rank">${index + 1}</div>
            <div class="track-thumb-wrap">
                <img src="${thumbUrl}" class="track-thumb" alt="${track.title || ''}" onerror="this.style.background='#222'">
                <div class="track-play-icon">
                    <svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>
                </div>
            </div>
            <div class="track-info">
                <div class="track-title">${track.title || 'Bilinmeyen'}</div>
                <div class="track-artist">${track.artist || ''}</div>
            </div>
            <button class="copy-btn" title="Şarkı adını kopyala" data-copy="${trackFullName.replace(/"/g, '&quot;')}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" stroke="currentColor" stroke-width="2" fill="none"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" stroke-width="2" fill="none"/></svg>
            </button>
        `;

        // Copy button handler — stop propagation so it doesn't trigger playback
        const copyBtn = card.querySelector('.copy-btn');
        copyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const text = copyBtn.dataset.copy;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.classList.add('copied');
                copyBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
                setTimeout(() => {
                    copyBtn.classList.remove('copied');
                    copyBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" stroke="currentColor" stroke-width="2" fill="none"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" stroke-width="2" fill="none"/></svg>';
                }, 1500);
            });
        });

        card.onclick = () => playTrack(track, card);
        list.appendChild(card);
    });
}

// ── Playback ──────────────────────────────
function playTrack(track, card) {
    const playerBar = document.getElementById('player-bar');
    const playerTitle = document.getElementById('player-title');
    const playerArtist = document.getElementById('player-artist');
    const playerThumb = document.getElementById('player-thumb');

    // Update player bar info
    playerTitle.textContent = track.title || '';
    playerArtist.textContent = track.artist || '';
    playerThumb.src = track.thumbnail || '';
    playerBar.classList.add('active');

    // Highlight playing card
    if (currentPlayingCard) currentPlayingCard.classList.remove('playing');
    card.classList.add('playing');
    currentPlayingCard = card;

    // Stop any current playback
    audioPlayer.pause();
    audioPlayer.src = '';
    ytIframe.src = '';

    // Determine playback method — prioritize previewUrl > videoId > externalUrl
    if (track.previewUrl) {
        // Deezer preview (30s MP3)
        playAudio(track.previewUrl);
    } else if (track.videoId) {
        // YouTube embed (works for YouTube Music, Spotify proxy, and Apple Music)
        playYouTube(track.videoId, track.duration || 180);
    } else if (track.externalUrl) {
        // Last resort: open externally
        window.open(track.externalUrl, '_blank');
    }
}

function playAudio(url) {
    audioPlayer.src = url;
    audioPlayer.play();
    isPlaying = true;
    updatePlayPauseIcon();

    audioPlayer.ontimeupdate = () => {
        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        document.getElementById('player-progress').style.width = progress + '%';
        document.getElementById('player-time').textContent = formatTime(audioPlayer.currentTime);
    };

    audioPlayer.onended = () => {
        isPlaying = false;
        updatePlayPauseIcon();
    };
}

function playYouTube(videoId, durationSec) {
    // Use YouTube IFrame API for embedded playback
    ytIframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&enablejsapi=1`;
    isPlaying = true;
    updatePlayPauseIcon();

    currentTrackDuration = durationSec;
    currentTrackTime = 0;
    
    clearInterval(ytProgressInterval);
    ytProgressInterval = setInterval(() => {
        if (isPlaying && currentTrackTime < currentTrackDuration) {
            currentTrackTime++;
            const progress = (currentTrackTime / currentTrackDuration) * 100;
            document.getElementById('player-progress').style.width = progress + '%';
            document.getElementById('player-time').textContent = formatTime(currentTrackTime);
        } else if (currentTrackTime >= currentTrackDuration) {
            clearInterval(ytProgressInterval);
            isPlaying = false;
            updatePlayPauseIcon();
        }
    }, 1000);
}

function updatePlayPauseIcon() {
    document.getElementById('play-icon').style.display = isPlaying ? 'none' : 'block';
    document.getElementById('pause-icon').style.display = isPlaying ? 'block' : 'none';
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// ── Player Controls ───────────────────────
document.getElementById('player-play-btn').addEventListener('click', () => {
    // Check if playing HTML5 audio (Deezer)
    if (audioPlayer.src && audioPlayer.src !== window.location.href) {
        if (audioPlayer.paused) {
            audioPlayer.play();
            isPlaying = true;
        } else {
            audioPlayer.pause();
            isPlaying = false;
        }
        updatePlayPauseIcon();
    } 
    // Otherwise, assume YouTube Iframe
    else if (ytIframe.src && ytIframe.src !== window.location.href) {
        if (isPlaying) {
            // Send pause command to YT Iframe
            ytIframe.contentWindow.postMessage('{"event":"command","func":"pauseVideo","args":""}', '*');
            isPlaying = false;
        } else {
            // Send play command to YT Iframe
            ytIframe.contentWindow.postMessage('{"event":"command","func":"playVideo","args":""}', '*');
            isPlaying = true;
        }
        updatePlayPauseIcon();
    }
});

document.getElementById('player-close-btn').addEventListener('click', () => {
    audioPlayer.pause();
    audioPlayer.src = '';
    ytIframe.src = '';
    clearInterval(ytProgressInterval);
    document.getElementById('player-bar').classList.remove('active');
    if (currentPlayingCard) currentPlayingCard.classList.remove('playing');
    currentPlayingCard = null;
    isPlaying = false;
    updatePlayPauseIcon();
});

// Progress bar click to seek
document.getElementById('player-progress-wrap').addEventListener('click', (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;

    if (audioPlayer.src && audioPlayer.src !== window.location.href && audioPlayer.duration) {
        audioPlayer.currentTime = ratio * audioPlayer.duration;
    } else if (ytIframe.src && ytIframe.src !== window.location.href && currentTrackDuration > 0) {
        currentTrackTime = ratio * currentTrackDuration;
        ytIframe.contentWindow.postMessage(JSON.stringify({
            "event": "command",
            "func": "seekTo",
            "args": [currentTrackTime, true]
        }), '*');
        
        // Update UI immediately
        const progress = (currentTrackTime / currentTrackDuration) * 100;
        document.getElementById('player-progress').style.width = progress + '%';
        document.getElementById('player-time').textContent = formatTime(currentTrackTime);
    }
});

// ── Initialize ────────────────────────────
window.onload = () => {
    // Add country selector event
    const countrySelect = document.getElementById('country-select');
    if (countrySelect) {
        countrySelect.addEventListener('change', (e) => {
            currentCountry = e.target.value;
            const countryName = e.target.options[e.target.selectedIndex].text.split(' ')[1] || e.target.options[e.target.selectedIndex].text;
            document.getElementById('main-subtitle').textContent = `Tüm Platformlardan ${countryName} Müzik Gündemi`;
            fetchTracks();
        });
    }
    
    fetchTracks();
};
