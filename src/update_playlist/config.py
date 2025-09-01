import re
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

        config_data = self._parse_config_file(config_path)
        return self._build_app_config(config_data)

    def _parse_config_file(self, config_path: Path) -> Dict[str, List[str]]:
        """Parse INI-style configuration file"""
        config_data = {}
        section_regex = re.compile(r'\[([a-zA-Z0-9_]+)\]')
        current_section = None

        with config_path.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                section_match = section_regex.match(line)
                if section_match:
                    current_section = section_match.group(1)
                    config_data.setdefault(current_section, [])
                    continue

                if current_section is None:
                    raise ValueError(f"Content outside section at line {line_num}")

                config_data[current_section].append(line)

        return config_data

    def _parse_playlist_line(self, line: str) -> tuple[str, Optional[str]]:
        """Parse a playlist line that may contain a name and optional URL"""
        parts = line.split(' ', 1)
        name = parts[0].strip()
        url = parts[1].strip() if len(parts) > 1 else None
        
        # Basic URL validation - check if it looks like a URL
        if url and not (url.startswith('http://') or url.startswith('https://')):
            # If the second part doesn't look like a URL, treat the whole line as the name
            name = line.strip()
            url = None
            
        return name, url

    def _build_app_config(self, config_data: Dict[str, List[str]]) -> AppConfig:
        """Build AppConfig from parsed data"""
        # Validate required sections
        if 'base' not in config_data or not config_data['base']:
            raise ValueError("Missing or empty 'base' section")

        if 'playlists' not in config_data:
            raise ValueError("Missing 'playlists' section")

        # Parse base path
        base_path = Path(config_data['base'][0]).expanduser().resolve()
        if not base_path.is_dir():
            raise ValueError(f"Base path is not a directory: {base_path}")

        # Parse playlists
        playlists = []
        for playlist_line in config_data['playlists']:
            if not playlist_line.strip():
                continue

            playlist_name, spotify_url = self._parse_playlist_line(playlist_line)
            folder_path = base_path / playlist_name
            
            playlists.append(PlaylistConfig(
                name=playlist_name,
                folder_path=folder_path,
                spotify_url=spotify_url
            ))

        # Parse Spotify credentials
        spotify_config = config_data.get('spotify', [])
        client_id = None
        client_secret = None
        audio_format = 'mp3'
        audio_quality = 'best'

        for line in spotify_config:
            if '=' in line:
                key, value = line.split('=', 1)
                key, value = key.strip(), value.strip()

                if key == 'client_id':
                    client_id = value
                elif key == 'client_secret':
                    client_secret = value
                elif key == 'audio_format':
                    audio_format = value
                elif key == 'audio_quality':
                    audio_quality = value

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

        default_config = """# Playlist Manager Configuration

# Base directory where playlists are stored
[base]
~/Music/playlists

# List of playlist folders to manage
# Format: playlist_name [optional_spotify_url]
[playlists]
# Add your playlist folder names here
# Examples:
# my-favorite-songs
# rock-classics https://open.spotify.com/playlist/4uV...
# jazz-collection https://open.spotify.com/playlist/37i...

# Spotify API credentials (optional but recommended)
# Get them from: https://developer.spotify.com/dashboard/applications
[spotify]
# client_id=your_client_id_here
# client_secret=your_client_secret_here
# audio_format=mp3
# audio_quality=best
"""

        config_path.write_text(default_config, encoding='utf-8')
        self.logger.info(f"Created default config: {config_path}")