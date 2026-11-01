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

## Configuration

Settings are taken from environment variables, or from the matching flag:

| Variable | Flag | Default |
|---|---|---|
| `MUSIC_DIR` | `--music-dir` | `~/Music/playlists` |
| `UPDATE_PLAYLIST_DB` | `--db` | `~/.local/share/update_playlist/playlists.db` |
| `AUDIO_FORMAT` | `--format` | `mp3` |
| `AUDIO_BITRATE` | `--bitrate` | `auto` |
| `UPDATE_PLAYLIST_LOG` | `--log-file` | `~/.cache/update_playlist/update_playlist.log` (empty = no log file) |
| `SPOTIFY_CLIENT_ID` | | spotDL's built-in credentials |
| `SPOTIFY_CLIENT_SECRET` | | spotDL's built-in credentials |

## Development

```bash
git clone https://github.com/totoLab/update_playlist.git
cd update_playlist
pip install -e . pytest
pytest
```
