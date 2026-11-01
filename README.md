# Update Playlist

Download Spotify playlists with [spotDL](https://github.com/spotDL/spotify-downloader) and keep them in sync. Each playlist gets its own folder and an `.m3u` file.

## Installation

```bash
pip install update-playlist
```

`ffmpeg` must be installed.

## Usage

Playlists are stored in a SQLite database.

```bash
update-playlist --add https://open.spotify.com/playlist/... rock-classics   # add and download
update-playlist --list
update-playlist --remove rock-classics   # downloaded files are kept
update-playlist                          # sync every playlist
```

Songs already on disk are skipped. Other flags: `--skip-sync` (only rebuild `.m3u` files), `--force-resync` (re-download everything), `-v`.

### Status page

`update-playlist --web 39501` keeps running and serves a live status page on http://localhost:39501: overall health, each playlist's state and song counts, last and next run, the recent log, and a **Sync now** button. Combine with `--interval HOURS` for scheduled syncs too.

The page has no authentication. It binds to `127.0.0.1` unless `WEB_HOST` says otherwise; in Docker it listens on all interfaces and compose publishes port 39501, so keep it on a trusted network.

### Upgrading from a config-file version

When the database is first created, playlists are imported automatically from `playlist.config` or `playlist.json`, found in `~/.config/update_playlist/`, `~/.config/playlist_manager/config.json`, or next to the database. Both the old text format and the JSON format work. Playlists without a URL get theirs from the `.spotdl` file in their folder. This happens once; delete the database to import again.

With Docker, copy the old file into `./data/` before the first run, and set `MUSIC_HOST_DIR` to your old music folder so songs you already have aren't downloaded again.

## Configuration

Settings are taken from environment variables, or from the matching flag:

| Variable | Flag | Default |
|---|---|---|
| `MUSIC_DIR` | `--music-dir` | `~/Music/playlists` |
| `UPDATE_PLAYLIST_DB` | `--db` | `~/.local/share/update_playlist/playlists.db` |
| `AUDIO_FORMAT` | `--format` | `mp3` |
| `AUDIO_BITRATE` | `--bitrate` | `auto` |
| `UPDATE_PLAYLIST_LOG` | `--log-file` | `~/.cache/update_playlist/update_playlist.log` (empty = no log file) |
| `WEB_PORT` | `--web` | off |
| `WEB_HOST` | `--web-host` | `127.0.0.1` (`0.0.0.0` in Docker) |
| `SPOTIFY_CLIENT_ID` | | spotDL's built-in credentials |
| `SPOTIFY_CLIENT_SECRET` | | spotDL's built-in credentials |

## Docker

```bash
cp .env.example .env        # optional: set MUSIC_HOST_DIR, Spotify credentials
mkdir -p music data         # create them yourself so they're owned by you, not root
docker compose run --rm update-playlist --add https://open.spotify.com/playlist/... rock-classics
docker compose up -d        # keeps running, syncs every 24 hours, status page on :39501
```

Any CLI command works through `docker compose run --rm update-playlist ...` (e.g. `--list`, `--remove NAME`, or no arguments for a one-off sync). The database lives in `./data`. The container runs as UID 1000; if your user has a different UID, add `user: "UID:GID"` to `compose.yaml`.

## Development

```bash
git clone https://github.com/totoLab/update_playlist.git
cd update_playlist
pip install -e . pytest
pytest
```
