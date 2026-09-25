from flask import Flask, jsonify, request
from ytmusicapi import YTMusic
import yt_dlp
import requests

# Hapus static_folder agar Vercel CDN yang menangani frontend
app = Flask(__name__)

ytmusic = YTMusic()

STREAM_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}

# ==========================================
# SEARCH
# ==========================================
@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Query pencarian kosong"}), 400

    try:
        songs = ytmusic.search(query, filter="songs", limit=10)
        results = []

        for song in songs:
            video_id = song.get("videoId")
            if not video_id:
                continue

            thumbnails = song.get("thumbnails") or []
            thumbnail = thumbnails[-1]["url"] if thumbnails else ""

            artists = song.get("artists") or []
            artist_name = ", ".join(a["name"] for a in artists if a.get("name")) or "Unknown"

            results.append({
                "id": video_id,
                "name": song.get("title", "Tanpa judul"),
                "artist_name": artist_name,
                "image": thumbnail,
                "audio": f"/api/stream/{video_id}",
            })

        return jsonify({"results": results})

    except Exception as error:
        print(error)
        return jsonify({"error": "Gagal mengambil data musik"}), 500

# ==========================================
# STREAM AUDIO (Redirect Direct URL)
# ==========================================
@app.route("/api/stream/<video_id>")
def api_stream(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"

        with yt_dlp.YoutubeDL(STREAM_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)

        audio_url = info.get("url")
        if not audio_url:
            formats = info.get("requested_formats") or info.get("formats")
            if formats:
                audio_url = formats[-1]["url"]

        if not audio_url:
            return jsonify({"error": "Audio tidak ditemukan"}), 404

        # Mengembalikan JSON direct URL agar tag <audio> frontend bisa langsung menyepelnya
        return jsonify({"url": audio_url})

    except Exception as error:
        print(error)
        return jsonify({"error": "Gagal mendapatkan audio URL"}), 500

# ==========================================
# LYRICS
# ==========================================
@app.route("/api/lyrics")
def api_lyrics():
    title = request.args.get("title", "").strip()
    artist = request.args.get("artist", "").strip()

    if not title:
        return jsonify({"error": "Judul lagu kosong"}), 400

    headers = {"User-Agent": "PyMusic/1.0"}

    def query_lrclib(track_name, artist_name=None):
        params = {"track_name": track_name}
        if artist_name:
            params["artist_name"] = artist_name

        response = requests.get(
            "https://lrclib.net/api/search",
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    try:
        results = query_lrclib(title, artist)
        if not results and artist:
            results = query_lrclib(title)

        if not results:
            return jsonify({"lyrics": None, "message": "Lirik tidak ditemukan"})

        best = results[0]
        return jsonify({
            "lyrics": best.get("plainLyrics"),
            "syncedLyrics": best.get("syncedLyrics"),
            "synced": bool(best.get("syncedLyrics")),
        })

    except Exception as error:
        print(error)
        return jsonify({"error": "Gagal mengambil lirik"}), 500

# ==========================================
# TEST ENDPOINT
# ==========================================
@app.route("/api/test")
def api_test():
    return jsonify({"message": "Server berhasil terhubung!"})

if __name__ == "__main__":
    app.run(port=3000, debug=True)
