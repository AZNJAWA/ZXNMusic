import yt_dlp
import requests
from flask import Flask, jsonify, request, Response, send_from_directory
from ytmusicapi import YTMusic

# ==========================================
# APP SETUP
# ==========================================

# Frontend files (index.html, Script.js, Style.css) live in ./frontend,
# same as with `app.use(express.static("frontend"))` in the old server.js.
app = Flask(__name__, static_folder="frontend", static_url_path="")

PORT = 3000

# No login/auth needed for public search.
ytmusic = YTMusic()

# Still used by /api/stream below — ytmusicapi finds songs, yt-dlp
# extracts the actual playable audio URL for a given videoId.
STREAM_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}


# ==========================================
# SERVE FRONTEND
# ==========================================

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ==========================================
# SEARCH  (via ytmusicapi — hits YouTube Music's own search, so results
# are actual songs with clean title/artist/album, not raw video titles)
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

            # Shaped to match what Script.js already expects
            # (song.name / song.artist_name / song.image / song.audio).
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
# STREAM AUDIO  (proxy, so the <audio> tag never touches googlevideo URLs
# directly — avoids CORS/expiry issues and supports seeking via Range)
# ==========================================

@app.route("/api/stream/<video_id>")
def api_stream(video_id):

    return jsonify({
        "debug": "STREAM ROUTE V2",
        "video_id": video_id
    })
    
@app.route("/api/stream/<video_id>")
def api_stream(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"

        print("================================")
        print("STREAM VIDEO ID:", video_id)
        print("STREAM URL:", url)

        with yt_dlp.YoutubeDL(STREAM_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)

        print("YT-DLP BERHASIL")
        print("TITLE:", info.get("title"))

        audio_url = info.get("url")

        if not audio_url:
            formats = info.get("requested_formats") or info.get("formats")

            if formats:
                audio_url = formats[-1].get("url")

        if not audio_url:
            print("AUDIO URL TIDAK DITEMUKAN")
            return jsonify({"error": "Audio tidak ditemukan"}), 404

        print("AUDIO URL BERHASIL DIDAPAT")

        range_header = request.headers.get("Range")

        upstream_headers = {}

        if range_header:
            upstream_headers["Range"] = range_header

        upstream = requests.get(
            audio_url,
            headers=upstream_headers,
            stream=True,
            timeout=30
        )

        print("UPSTREAM STATUS:", upstream.status_code)
        print("CONTENT TYPE:", upstream.headers.get("Content-Type"))

        def generate():
            for chunk in upstream.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        response_headers = {
            "Content-Type": upstream.headers.get(
                "Content-Type",
                "audio/mpeg"
            ),
            "Accept-Ranges": "bytes",
        }

        if "Content-Length" in upstream.headers:
            response_headers["Content-Length"] = upstream.headers["Content-Length"]

        if "Content-Range" in upstream.headers:
            response_headers["Content-Range"] = upstream.headers["Content-Range"]

        status_code = upstream.status_code if range_header else 200

        return Response(
            generate(),
            status=status_code,
            headers=response_headers
        )

    except Exception as error:
        import traceback

        print("================================")
        print("STREAM ERROR:")
        traceback.print_exc()
        print("================================")

        return jsonify({
            "error": str(error)
        }), 500

# ==========================================
# LYRICS  (via lrclib.net — free, no API key needed)
# ==========================================

@app.route("/api/lyrics")
def api_lyrics():
    title = request.args.get("title", "").strip()
    artist = request.args.get("artist", "").strip()

    if not title:
        return jsonify({"error": "Judul lagu kosong"}), 400

    # lrclib rejects/ignores requests without a proper User-Agent.
    headers = {"User-Agent": "PyMusic v1.0 (https://github.com/your-repo)"}

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

        # Some YouTube Music artist names don't match lrclib's database
        # exactly — retry without the artist filter before giving up.
        if not results and artist:
            results = query_lrclib(title)

        if not results:
            return jsonify({"lyrics": None, "message": "Lirik tidak ditemukan"})

        best = results[0]
        plain_lyrics = best.get("plainLyrics")
        synced_lyrics = best.get("syncedLyrics")

        return jsonify({
            "lyrics": plain_lyrics,
            "syncedLyrics": synced_lyrics,
            "synced": bool(synced_lyrics),
        })

    except Exception as error:
        print(error)
        return jsonify({"error": "Gagal mengambil lirik"}), 500


# ==========================================
# TEST ENDPOINT  (same as the old /api/test)
# ==========================================

@app.route("/api/test")
def api_test():
    return jsonify({"message": "Server berhasil terhubung!"})


if __name__ == "__main__":
    print(f"Server berjalan di http://localhost:{PORT}")
    # threaded=True matters here: /api/stream holds a connection open
    # while it proxies audio, so without this a concurrent /api/search
    # (or another /api/stream) can hang or get its connection reset.
    app.run(port=PORT, debug=True, threaded=True)
