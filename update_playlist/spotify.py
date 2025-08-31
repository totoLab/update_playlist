import os
import logging
from pathlib import Path
from typing import Dict, List

from spotdl import Spotdl
from spotdl.utils.config import get_config
from spotdl.types.song import Song


class SpotDLWrapper:
    """Wrapper class for SpotDL operations"""

    def __init__(self, client_id: str = None, client_secret: str = None,
                 audio_format: str = 'mp3', audio_quality: str = 'best',
                 logger: logging.Logger = None):
        """Initialize SpotDL wrapper"""
        self.logger = logger or logging.getLogger(__name__)
        self.client = None
        self.audio_format = audio_format
        self.audio_quality = audio_quality

        self._initialize_client(client_id, client_secret)

    def _initialize_client(self, client_id: str = None, client_secret: str = None) -> None:
        """Initialize the SpotDL client"""
        try:
            config = get_config()

            # Override with provided credentials
            if client_id:
                config['client_id'] = client_id
            if client_secret:
                config['client_secret'] = client_secret

            # Set audio preferences
            config['format'] = self.audio_format
            config['quality'] = self.audio_quality

            self.client = Spotdl(
                client_id=config.get('client_id', ''),
                client_secret=config.get('client_secret', ''),
                no_cache=False,
                headless=True,
            )

            self.logger.info("SpotDL client initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize SpotDL client: {e}")
            raise

    def search_playlist(self, spotify_url: str) -> List[Song]:
        """Search for songs in a Spotify playlist/album/track"""
        try:
            self.logger.info(f"Searching songs from: {spotify_url}")
            songs = self.client.search([spotify_url])
            self.logger.info(f"Found {len(songs)} songs")
            return songs

        except Exception as e:
            self.logger.error(f"Failed to search playlist {spotify_url}: {e}")
            return []

    def download_songs(self, songs: List[Song], download_path: Path) -> List[bool]:
        """Download a list of songs to the specified path"""
        if not songs:
            return []

        try:
            self.logger.info(f"Downloading {len(songs)} songs to {download_path}")

            # Change to download directory
            original_cwd = os.getcwd()
            os.chdir(download_path)

            try:
                results = self.client.download_songs(songs)
                successful = sum(1 for result in results if result)
                self.logger.info(f"Successfully downloaded {successful}/{len(songs)} songs")
                return results

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            self.logger.error(f"Failed to download songs: {e}")
            return [False] * len(songs)

    def get_playlist_metadata(self, spotify_url: str) -> Dict:
        """Get metadata for a playlist"""
        try:
            # Extract basic info from URL
            if 'playlist' in spotify_url:
                playlist_id = spotify_url.split('/')[-1].split('?')[0]
                return {
                    'type': 'playlist',
                    'id': playlist_id,
                    'url': spotify_url
                }
            elif 'album' in spotify_url:
                album_id = spotify_url.split('/')[-1].split('?')[0]
                return {
                    'type': 'album',
                    'id': album_id,
                    'url': spotify_url
                }
            else:
                return {
                    'type': 'track',
                    'url': spotify_url
                }

        except Exception as e:
            self.logger.error(f"Failed to get playlist metadata: {e}")
            return {}
