# ── PosterForge — single-container Docker image ──────────────────────────────
# Python Flask backend + static frontend served from the same container.
# Build:  docker build -t posterforge:latest .
# Run:    docker run -d -p 8090:5000 \
#           -e TMDB_API_KEY=your_key_here \
#           -v /mnt/user/appdata/posterforge/output:/app/output \
#           --name posterforge posterforge:latest

FROM python:3.12-slim

# System deps for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg-turbo-progs libpng-dev libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/app.py ./

# Copy frontend (plain HTML — no build step needed)
COPY frontend/index.html ./frontend/dist/index.html

# Output folder placeholder (overridden by volume mount)
RUN mkdir -p /app/output

# Gunicorn serves the Flask app
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
