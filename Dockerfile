FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 1000 app \
    && mkdir /music /data && chown app:app /music /data
USER app

ENV MUSIC_DIR=/music \
    UPDATE_PLAYLIST_DB=/data/playlists.db \
    UPDATE_PLAYLIST_LOG= \
    WEB_HOST=0.0.0.0

EXPOSE 39501

VOLUME ["/music", "/data"]
ENTRYPOINT ["update-playlist"]
