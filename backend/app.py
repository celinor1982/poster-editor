from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import base64
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
CORS(app)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG  = "https://image.tmdb.org/t/p/w500"


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


# ── TMDB search ──────────────────────────────────────────────────────────────

@app.route("/api/search")
def search():
    query    = request.args.get("q", "")
    media    = request.args.get("type", "movie")   # movie | tv
    page     = request.args.get("page", 1)

    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY not set"}), 500

    endpoint = f"{TMDB_BASE}/search/{media}"
    r = requests.get(endpoint, params={
        "api_key": TMDB_API_KEY,
        "query":   query,
        "page":    page,
    }, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = []
    for item in data.get("results", []):
        poster = item.get("poster_path")
        results.append({
            "id":         item["id"],
            "title":      item.get("title") or item.get("name", ""),
            "year":       (item.get("release_date") or item.get("first_air_date") or "")[:4],
            "poster_url": f"{TMDB_IMG}{poster}" if poster else None,
            "type":       media,
        })

    return jsonify({"results": results, "total_pages": data.get("total_pages", 1)})


# ── Proxy TMDB image so the browser doesn't need direct TMDB access ──────────

@app.route("/api/proxy-image")
def proxy_image():
    url = request.args.get("url", "")
    if not url.startswith("https://image.tmdb.org"):
        return jsonify({"error": "Only TMDB images may be proxied"}), 400
    r = requests.get(url, timeout=15)
    return app.response_class(r.content, mimetype=r.headers["Content-Type"])


# ── Save edited poster ────────────────────────────────────────────────────────

@app.route("/api/save", methods=["POST"])
def save_poster():
    data     = request.json
    filename = data.get("filename", "poster.jpg").replace("/", "_").replace("..", "")
    image_b64 = data.get("image")          # data-URL from canvas

    if not image_b64:
        return jsonify({"error": "No image data"}), 400

    # Strip data-URL header
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    img_bytes = base64.b64decode(image_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    out_path = os.path.join(OUTPUT_DIR, filename)
    img.save(out_path, "JPEG", quality=95)

    return jsonify({"saved": filename, "path": out_path})


# ── List saved posters ────────────────────────────────────────────────────────

@app.route("/api/saved")
def list_saved():
    files = []
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            files.append(f)
    return jsonify({"files": files})


@app.route("/api/saved/<filename>")
def get_saved(filename):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
