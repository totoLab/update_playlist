# Update Playlist

A modular playlist manager to download and manage Spotify playlists.

## Installation

Install the package from PyPI:

```bash
pip install update-playlist
```

## Usage

1.  **Configuration**

    The first time you run `update-playlist`, it will create a default configuration file at `~/.config/update_playlist/playlist.config`. You need to edit this file to configure your playlists.

    ```ini
    # Playlist Manager Configuration

    # Base directory where playlists are stored
    [base]
    ~/Music/playlists

    # List of playlist folders to manage
    [playlists]
    # Add your playlist folder names here
    # Example:
    # my-favorite-songs
    # rock-classics

    # Spotify API credentials (optional but recommended)
    # Get them from: https://developer.spotify.com/dashboard/applications
    [spotify]
    # client_id=your_client_id_here
    # client_secret=your_client_secret_here
    # audio_format=mp3
    # audio_quality=best
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