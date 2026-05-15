from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from ytmusicapi import YTMusic
import uvicorn
import os
import requests

app = FastAPI()

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create frontend directory if it doesn't exist
if not os.path.exists("frontend"):
    os.makedirs("frontend")

# Serve static files — must be AFTER API routes, so we define it later
yt = YTMusic()

# ─────────────────── YouTube Music ───────────────────

@app.get("/api/youtube/top")
async def yt_top_10():
    try:
        # get_charts returns playlists (e.g. "Trending 20 Turkey"), not individual songs.
        # We extract the first playlist and fetch its tracks.
        charts = yt.get_charts(country='TR')
        videos = charts.get('videos', [])
        
        # In some ytmusicapi versions, videos is a dict with 'items'
        if isinstance(videos, dict):
            videos = videos.get('items', [])
            
        tracks_raw = []
        
        # Check if the returned items are playlists (like "Trending 20 Turkey")
        if videos and isinstance(videos, list) and videos[0].get('playlistId'):
            try:
                playlist = yt.get_playlist(videos[0]['playlistId'])
                tracks_raw = playlist.get('tracks', [])
            except Exception as e:
                print("Playlist fetch error:", e)
        # If they are already songs
        elif videos and isinstance(videos, list) and videos[0].get('videoId'):
            tracks_raw = videos
        
        # Fallback to search if everything fails
        if not tracks_raw:
            tracks_raw = yt.search("Türkiye trend şarkılar", filter="songs")
        
        result = []
        for t in tracks_raw[:10]:
            thumb = ''
            if t.get('thumbnails'):
                thumb = t['thumbnails'][-1]['url']
            artists = ''
            if t.get('artists'):
                artists = ', '.join(a['name'] for a in t['artists'])
            result.append({
                'title': t.get('title', ''),
                'artist': artists,
                'thumbnail': thumb,
                'videoId': t.get('videoId', ''),
                'platform': 'youtube',
            })
        return result
    except Exception as e:
        print(f"YT Top Error: {e}")
        return []

@app.get("/api/youtube/new")
async def yt_new_releases():
    try:
        new_releases = yt.search("yeni çıkanlar 2026", filter="songs")
        result = []
        for t in new_releases[:10]:
            thumb = ''
            if t.get('thumbnails'):
                thumb = t['thumbnails'][-1]['url']
            artists = ''
            if t.get('artists'):
                artists = ', '.join(a['name'] for a in t['artists'])
            result.append({
                'title': t.get('title', ''),
                'artist': artists,
                'thumbnail': thumb,
                'videoId': t.get('videoId', ''),
                'platform': 'youtube',
            })
        return result
    except Exception as e:
        print(f"YT New Error: {e}")
        return []

# ─────────────────── Spotify ───────────────────
# Uses ytmusicapi search as a proxy since Spotify requires OAuth.
# We search YTMusic for Spotify-popular Turkish songs.

@app.get("/api/spotify/top")
async def spotify_top_10():
    try:
        results = yt.search("Spotify Türkiye Top 10", filter="songs")
        out = []
        for t in results[:10]:
            thumb = ''
            if t.get('thumbnails'):
                thumb = t['thumbnails'][-1]['url']
            artists = ''
            if t.get('artists'):
                artists = ', '.join(a['name'] for a in t['artists'])
            out.append({
                'title': t.get('title', ''),
                'artist': artists,
                'thumbnail': thumb,
                'videoId': t.get('videoId', ''),
                'platform': 'spotify',
            })
        return out
    except Exception as e:
        print(f"Spotify Top Error: {e}")
        return []

@app.get("/api/spotify/new")
async def spotify_new():
    try:
        results = yt.search("Spotify yeni çıkanlar Türkiye 2026", filter="songs")
        out = []
        for t in results[:10]:
            thumb = ''
            if t.get('thumbnails'):
                thumb = t['thumbnails'][-1]['url']
            artists = ''
            if t.get('artists'):
                artists = ', '.join(a['name'] for a in t['artists'])
            out.append({
                'title': t.get('title', ''),
                'artist': artists,
                'thumbnail': thumb,
                'videoId': t.get('videoId', ''),
                'platform': 'spotify',
            })
        return out
    except Exception as e:
        print(f"Spotify New Error: {e}")
        return []

# ─────────────────── Deezer ───────────────────

@app.get("/api/deezer/top")
async def deezer_top_10():
    try:
        resp = requests.get("https://api.deezer.com/chart/0/tracks?limit=10", timeout=10)
        data = resp.json().get('data', [])
        result = []
        for t in data:
            result.append({
                'title': t.get('title', ''),
                'artist': t.get('artist', {}).get('name', ''),
                'thumbnail': t.get('album', {}).get('cover_medium', ''),
                'previewUrl': t.get('preview', ''),
                'externalUrl': t.get('link', ''),
                'platform': 'deezer',
            })
        return result
    except Exception as e:
        print(f"Deezer Top Error: {e}")
        return []

@app.get("/api/deezer/new")
async def deezer_new():
    try:
        # Search Deezer for new Turkish songs
        resp = requests.get("https://api.deezer.com/search?q=yeni+türkçe+pop&order=RATING_DESC&limit=10", timeout=10)
        data = resp.json().get('data', [])
        result = []
        for t in data:
            result.append({
                'title': t.get('title', ''),
                'artist': t.get('artist', {}).get('name', ''),
                'thumbnail': t.get('album', {}).get('cover_medium', ''),
                'previewUrl': t.get('preview', ''),
                'externalUrl': t.get('link', ''),
                'platform': 'deezer',
            })
        return result
    except Exception as e:
        print(f"Deezer New Error: {e}")
        return []

# ─────────────────── Apple Music ───────────────────

def _find_yt_video_id(title, artist):
    """Search YouTube Music for a song and return its videoId for inline playback."""
    try:
        query = f"{title} {artist}"
        results = yt.search(query, filter="songs", limit=1)
        if results:
            return results[0].get('videoId', '')
    except Exception:
        pass
    return ''

@app.get("/api/apple/top")
async def apple_top_10():
    try:
        resp = requests.get("https://rss.applemarketingtools.com/api/v2/tr/music/most-played/10/songs.json", timeout=10)
        data = resp.json().get('feed', {}).get('results', [])
        result = []
        for t in data:
            title = t.get('name', '')
            artist = t.get('artistName', '')
            video_id = _find_yt_video_id(title, artist)
            result.append({
                'title': title,
                'artist': artist,
                'thumbnail': t.get('artworkUrl100', '').replace('100x100', '300x300'),
                'videoId': video_id,
                'externalUrl': t.get('url', ''),
                'platform': 'apple',
            })
        return result
    except Exception as e:
        print(f"Apple Top Error: {e}")
        return []

@app.get("/api/apple/new")
async def apple_new():
    try:
        # Apple Music RSS feeds for new releases return 404 for Turkey.
        # So we use YTMusic as a proxy to search for "Apple Music yeni çıkanlar"
        results = yt.search("Apple Music yeni çıkanlar Türkiye", filter="songs")
        out = []
        for t in results[:10]:
            thumb = ''
            if t.get('thumbnails'):
                thumb = t['thumbnails'][-1]['url']
            artists = ''
            if t.get('artists'):
                artists = ', '.join(a['name'] for a in t['artists'])
            
            # Since we fetched directly from YT, we already have the videoId
            out.append({
                'title': t.get('title', ''),
                'artist': artists,
                'thumbnail': thumb,
                'videoId': t.get('videoId', ''),
                'platform': 'apple',
            })
        return out
    except Exception as e:
        print(f"Apple New Error: {e}")
        return []

# ─────────────────── Static Files & Index ───────────────────

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("frontend/index.html")

@app.get("/manifest.json")
async def read_manifest():
    return FileResponse("frontend/manifest.json")

@app.get("/sw.js")
async def read_sw():
    return FileResponse("frontend/sw.js", media_type="application/javascript")

@app.get("/icon.png")
async def read_icon():
    return FileResponse("frontend/icon.png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
