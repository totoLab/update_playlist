import re
import json
import logging
import datetime
from pathlib import Path
from typing import List, Set, Optional

from spotdl.types.song import Song


class FileManager:
    """Handles file system operations"""

    MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.mkv', '.avi', '.flac', '.wav', '.aac', '.ogg', '.opus'}

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    def get_media_files(self, folder_path: Path) -> List[Path]:
        """Get all media files in a folder"""
        media_files = []
        for file_path in folder_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.MEDIA_EXTENSIONS:
                media_files.append(file_path)
        return sorted(media_files)

    def create_m3u_playlist(self, folder_path: Path, output_file: Path = None) -> Path:
        """Create an M3U playlist file from media files in a folder"""
        if output_file is None:
            output_file = folder_path / f"{folder_path.name}.m3u"

        try:
            media_files = self.get_media_files(folder_path)

            with output_file.open('w', encoding='utf-8') as f:
                f.write('#EXTM3U\\n')
                for media_file in media_files:
                    relative_path = media_file.relative_to(folder_path)
                    f.write(f'{relative_path}\\n')

            self.logger.info(f'M3U playlist created: {output_file} ({len(media_files)} files)')
            return output_file

        except Exception as e:
            self.logger.error(f'Failed to create M3U playlist: {e}')
            raise

    def load_spotdl_file(self, spotdl_file: Path) -> Optional[str]:
        """Load Spotify URL from a .spotdl file"""
        try:
            content = spotdl_file.read_text(encoding='utf-8').strip()

            # Handle direct URL
            if content.startswith('http'):
                return content

            # Handle JSON format
            try:
                data = json.loads(content)
                return data.get('query') or data.get('url')
            except json.JSONDecodeError:
                pass

            self.logger.warning(f"Could not parse .spotdl file: {spotdl_file}")
            return None

        except Exception as e:
            self.logger.error(f"Failed to read .spotdl file {spotdl_file}: {e}")
            return None

    def save_spotdl_file(self, spotify_url: str, output_file: Path) -> None:
        """Save Spotify URL to a .spotdl file"""
        try:
            metadata = {
                'query': spotify_url,
                'created_at': datetime.datetime.now().isoformat(),
                'format': 'json'
            }

            with output_file.open('w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            self.logger.info(f"Saved .spotdl file: {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to save .spotdl file: {e}")
            raise

    def get_existing_songs(self, folder_path: Path) -> Set[str]:
        """Get normalized names of existing songs"""
        existing = set()
        media_files = self.get_media_files(folder_path)

        for file_path in media_files:
            # Normalize filename for comparison
            name = file_path.stem.lower()
            name = re.sub(r'[^\w\s-]', '', name).strip()
            name = re.sub(r'[-\s]+', '-', name)
            existing.add(name)

        return existing

    def normalize_song_name(self, song: Song) -> str:
        """Create normalized filename from song metadata"""
        name = f"{song.artist} - {song.name}".lower()
        name = re.sub(r'[^\w\s-]', '', name).strip()
        name = re.sub(r'[-\s]+', '-', name)
        return name
