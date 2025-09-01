# Update Playlist

A modular playlist manager to download and manage Spotify playlists.

## Installation

Install the package from PyPI:

```bash
pip install update-playlist
```

## Usage

1.  **Configuration**

    The first time you run `update-playlist`, it will create a default configuration file at `~/.config/update_playlist/playlist.json`. You need to edit this file to configure your playlists.

    ```json
    {
        "base_path": "~/Music/playlists",
        "playlists": [
            {
                "name": "my-favorite-songs"
            },
            {
                "name": "rock-classics",
                "spotify_url": "https://open.spotify.com/playlist/4uV..."
            }
        ],
        "spotify": {
            "client_id": "your_client_id_here",
            "client_secret": "your_client_secret_here",
            "audio_format": "mp3",
            "audio_quality": "best"
        }
    }
    ```

2.  **Sync Playlists**

    To sync all your playlists, run:

    ```bash
    update-playlist
    ```

3.  **Add a new playlist**

    You can add a new playlist using the `--add-playlist` option:

    ```bash
    update-playlist --add-playlist <SPOTIFY_URL> <PLAYLIST_NAME>
    ```

## Development

To install the project in editable mode:

```bash
git clone https://github.com/your-username/update-playlist.git
cd update-playlist
pip install -e .
```