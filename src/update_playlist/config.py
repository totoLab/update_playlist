import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DEFAULT_CONFIG = {
    "base_path": "~/Music/playlists",
    "playlists": [
        {"name": "rock-classics", "spotify_url": "https://open.spotify.com/playlist/4uV..."},
    ],
    "spotify": {
        "client_id": "",
        "client_secret": "",
        "audio_format": "mp3",
        "bitrate": "auto",
    },
}


@dataclass
class PlaylistConfig:
    name: str
    folder_path: Path
    spotify_url: Optional[str] = None


@dataclass
class AppConfig:
    base_path: Path
    playlists: List[PlaylistConfig]
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    audio_format: str = 'mp3'
    bitrate: str = 'auto'


def load_config(config_path: Path) -> AppConfig:
    data = json.loads(config_path.read_text(encoding='utf-8'))
    for key in ('base_path', 'playlists'):
        if key not in data:
            raise ValueError(f"Missing '{key}' in config")

    base_path = Path(data['base_path']).expanduser().resolve()
    base_path.mkdir(parents=True, exist_ok=True)

    playlists = []
    for p in data['playlists']:
        if not isinstance(p, dict) or 'name' not in p:
            raise ValueError(f"Invalid playlist configuration: {p!r}")
        playlists.append(PlaylistConfig(p['name'], base_path / p['name'], p.get('spotify_url')))

    spotify = data.get('spotify', {})
    return AppConfig(
        base_path=base_path,
        playlists=playlists,
        spotify_client_id=spotify.get('client_id') or None,
        spotify_client_secret=spotify.get('client_secret') or None,
        audio_format=spotify.get('audio_format', 'mp3'),
        bitrate=spotify.get('bitrate', 'auto'),
    )


def create_default_config(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=4) + '\n', encoding='utf-8')


def add_playlist(config_path: Path, name: str, spotify_url: str) -> None:
    data = json.loads(config_path.read_text(encoding='utf-8'))
    data['playlists'].append({'name': name, 'spotify_url': spotify_url})
    config_path.write_text(json.dumps(data, indent=4) + '\n', encoding='utf-8')
