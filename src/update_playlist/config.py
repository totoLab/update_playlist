import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PlaylistConfig:
    """Configuration for a single playlist"""
    name: str
    folder_path: Path
    spotify_url: Optional[str] = None
    spotdl_file: Optional[Path] = None


@dataclass
class AppConfig:
    """Main application configuration"""
    base_path: Path
    playlists: List[PlaylistConfig]
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    audio_format: str = 'mp3'
    audio_quality: str = 'best'


class ConfigManager:
    """Handles configuration parsing and management"""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    def load_config(self, config_path: Path) -> AppConfig:
        """Load configuration from file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        config_data = self._parse_json_file(config_path)
        return self._build_app_config(config_data)

    def _parse_json_file(self, config_path: Path) -> Dict:
        """Parse JSON configuration file"""
        with config_path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _build_app_config(self, config_data: Dict) -> AppConfig:
        """Build AppConfig from parsed data"""
        # Validate required sections
        if 'base_path' not in config_data:
            raise ValueError("Missing 'base_path' in config")

        if 'playlists' not in config_data:
            raise ValueError("Missing 'playlists' in config")

        # Parse base path
        base_path = Path(config_data['base_path']).expanduser().resolve()
        if not base_path.is_dir():
            raise ValueError(f"Base path is not a directory: {base_path}")

        # Parse playlists
        playlists = []
        for playlist_data in config_data['playlists']:
            if not isinstance(playlist_data, dict) or 'name' not in playlist_data:
                raise ValueError("Invalid playlist configuration")

            playlist_name = playlist_data['name']
            spotify_url = playlist_data.get('spotify_url')
            folder_path = base_path / playlist_name
            
            playlists.append(PlaylistConfig(
                name=playlist_name,
                folder_path=folder_path,
                spotify_url=spotify_url
            ))

        # Parse Spotify credentials
        spotify_config = config_data.get('spotify', {})
        client_id = spotify_config.get('client_id')
        client_secret = spotify_config.get('client_secret')
        audio_format = spotify_config.get('audio_format', 'mp3')
        audio_quality = spotify_config.get('audio_quality', 'best')

        return AppConfig(
            base_path=base_path,
            playlists=playlists,
            spotify_client_id=client_id,
            spotify_client_secret=client_secret,
            audio_format=audio_format,
            audio_quality=audio_quality
        )

    def create_default_config(self, config_path: Path) -> None:
        """Create a default configuration file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "base_path": "~/Music/playlists",
            "playlists": [
                {
                    "name": "my-favorite-songs"
                },
                {
                    "name": "rock-classics",
                    "spotify_url": "https://open.spotify.com/playlist/4uV..."
                },
                {
                    "name": "jazz-collection",
                    "spotify_url": "https://open.spotify.com/playlist/37i..."
                }
            ],
            "spotify": {
                "client_id": "your_client_id_here",
                "client_secret": "your_client_secret_here",
                "audio_format": "mp3",
                "audio_quality": "best"
            }
        }

        with config_path.open('w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)

        self.logger.info(f"Created default config: {config_path}")

    def get_config_path(self, config_arg: Optional[str] = None) -> Path:
        """Determine the configuration file path"""
        if config_arg:
            return Path(config_arg)

        # Default search paths
        search_paths = [
            Path('playlist.json'),
            Path.home() / '.config/playlist_manager/config.json',
            Path('/etc/playlist_manager/config.json')
        ]

        for path in search_paths:
            if path.exists():
                return path

        # If no config found, create a default one in the current directory
        default_path = Path('playlist.json')
        self.create_default_config(default_path)
        return default_path