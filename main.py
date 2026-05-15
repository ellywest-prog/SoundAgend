from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
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
# We set location to 'TR' so that US-based cloud servers (like Render) can fetch Turkish charts correctly by default.
yt = YTMusic(language="tr", location="TR")

COUNTRY_NAMES = {
    "TR": "Türkiye",
    "US": "Amerika",
    "GB": "İngiltere",
    "DE": "Almanya",
    "FR": "Fransa",
    "IT": "İtalya",
    "ES": "İspanya",
    "BR": "Brezilya",
    "MX": "Meksika",
    "JP": "Japonya",
    "KR": "Güney Kore",
    "IN": "Hindistan"
}

COUNTRY_NAMES_EN = {
    "TR": "Turkey",
    "US": "USA",
    "GB": "UK",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "BR": "Brazil",
    "MX": "Mexico",
    "JP": "Japan",
    "KR": "South Korea",
    "IN": "India"
}

# ─────────────────── YouTube Music ───────────────────

@app.get("/api/youtube/top")
async def yt_top_20(country: str = "TR", limit: int = 20):
    try:
        c_name_en = COUNTRY_NAMES_EN.get(country.upper(), "Turkey")
        # Instantiate localized YTMusic for this request to ensure no geo-blocks
        yt_local = YTMusic(language="tr", location=country.upper())
        
        videos = []
        if limit <= 20:
            try:
                charts = yt_local.get_charts(country=country.upper())
                videos = charts.get('videos', [])
            except Exception as e:
                print("YT get_charts error:", e)
            
        # In some ytmusicapi versions, videos is a dict with 'items'
        if isinstance(videos, dict):
            videos = videos.get('items', [])
            
        tracks_raw = []
        
        # Check if the returned items are playlists (like "Trending 20 Turkey")
        if videos and isinstance(videos, list) and videos[0].get('playlistId'):
            try:
                playlist = yt_local.get_playlist(videos[0]['playlistId'], limit=limit)
                tracks_raw = playlist.get('tracks', [])
            except Exception as e:
                print("Playlist fetch error:", e)
        # If they are already songs
        elif videos and isinstance(videos, list) and videos[0].get('videoId'):
            tracks_raw = videos
        
        # Fallback to search if everything fails
        if not tracks_raw:
            tracks_raw = yt_local.search(f"Top 50 songs {c_name_en}", filter="songs", limit=limit)
        
        result = []
        for t in tracks_raw[:limit]:
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
                'duration': t.get('duration_seconds', 180),
                'platform': 'youtube',
            })
        return result
    except Exception as e:
        print(f"YT Top Error: {e}")
        return []

@app.get("/api/youtube/new")
async def yt_new_releases(country: str = "TR", limit: int = 20):
    try:
        c_name_en = COUNTRY_NAMES_EN.get(country.upper(), "Turkey")
        yt_local = YTMusic(language="tr", location=country.upper())
        query = f"new release songs {c_name_en}"
        new_releases = yt_local.search(query, filter="songs", limit=limit)
        result = []
        for t in new_releases[:limit]:
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
                'duration': t.get('duration_seconds', 180),
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
async def spotify_top_20(country: str = "TR", limit: int = 20):
    try:
        c_name_en = COUNTRY_NAMES_EN.get(country.upper(), "Turkey")
        yt_local = YTMusic(language="tr", location=country.upper())
        results = yt_local.search(f"Spotify Top 50 {c_name_en}", filter="songs", limit=limit)
        out = []
        for t in results[:limit]:
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
                'duration': t.get('duration_seconds', 180),
                'platform': 'spotify',
            })
        return out
    except Exception as e:
        print(f"Spotify Top Error: {e}")
        return []

@app.get("/api/spotify/new")
async def spotify_new(country: str = "TR", limit: int = 20):
    try:
        c_name_en = COUNTRY_NAMES_EN.get(country.upper(), "Turkey")
        yt_local = YTMusic(language="tr", location=country.upper())
        query = f"Spotify new releases {c_name_en}"
        results = yt_local.search(query, filter="songs", limit=limit)
        out = []
        for t in results[:limit]:
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
                'duration': t.get('duration_seconds', 180),
                'platform': 'spotify',
            })
        return out
    except Exception as e:
        print(f"Spotify New Error: {e}")
        return []



# ─────────────────── Apple Music ───────────────────

def _find_yt_video_id(title, artist):
    """Search YouTube Music for a song and return its videoId and duration_seconds for inline playback."""
    try:
        query = f"{title} {artist}"
        results = yt.search(query, filter="songs", limit=1)
        if results:
            return results[0].get('videoId', ''), results[0].get('duration_seconds', 180)
    except Exception:
        pass
    return '', 180

@app.get("/api/apple/top")
async def apple_top_20(country: str = "TR", limit: int = 20):
    try:
        c_code = country.lower()
        resp = requests.get(f"https://rss.applemarketingtools.com/api/v2/{c_code}/music/most-played/50/songs.json", timeout=10)
        data = resp.json().get('feed', {}).get('results', [])
        result = []
        for t in data[:limit]:
            title = t.get('name', '')
            artist = t.get('artistName', '')
            video_id, duration = _find_yt_video_id(title, artist)
            result.append({
                'title': title,
                'artist': artist,
                'thumbnail': t.get('artworkUrl100', '').replace('100x100', '300x300'),
                'videoId': video_id,
                'externalUrl': t.get('url', ''),
                'duration': duration,
                'platform': 'apple',
            })
        return result
    except Exception as e:
        print(f"Apple Top Error: {e}")
        return []

@app.get("/api/apple/new")
async def apple_new(country: str = "TR", limit: int = 20):
    try:
        c_name_en = COUNTRY_NAMES_EN.get(country.upper(), "Turkey")
        
        # Apple Music RSS feeds for new releases return 404 for Turkey and some others.
        # So we use YTMusic as a proxy to search for new releases.
        yt_local = YTMusic(language="tr", location=country.upper())
        results = yt_local.search(f"Apple Music new releases {c_name_en}", filter="songs", limit=limit)
        out = []
        for t in results[:limit]:
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
                'duration': t.get('duration_seconds', 180),
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
