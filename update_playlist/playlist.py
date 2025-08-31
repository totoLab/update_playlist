import sys
import logging
import datetime
from pathlib import Path
from typing import List, Optional

from spotdl.types.song import Song

from .config import PlaylistConfig, ConfigManager
from .spotify import SpotDLWrapper
from .file_manager import FileManager


class PlaylistSyncer:
    """Handles playlist synchronization logic"""

    def __init__(self, spotdl_wrapper: SpotDLWrapper, file_manager: FileManager,
                 logger: logging.Logger = None):
        self.spotdl = spotdl_wrapper
        self.file_manager = file_manager
        self.logger = logger or logging.getLogger(__name__)

    def sync_playlist(self, playlist_config: PlaylistConfig, force_resync: bool = False) -> bool:
        """Sync a single playlist"""
        try:
            self.logger.info(f"Syncing playlist: {playlist_config.name}")

            # Ensure folder exists
            playlist_config.folder_path.mkdir(parents=True, exist_ok=True)

            # Get Spotify URL
            spotify_url = self._get_spotify_url(playlist_config)
            if not spotify_url:
                return False

            # Search for songs
            songs = self.spotdl.search_playlist(spotify_url)
            if not songs:
                self.logger.warning(f"No songs found for {playlist_config.name}")
                return False

            # Filter songs that need downloading
            if not force_resync:
                songs_to_download = self._filter_new_songs(songs, playlist_config.folder_path)
            else:
                songs_to_download = songs

            # Download new songs
            if songs_to_download:
                results = self.spotdl.download_songs(songs_to_download, playlist_config.folder_path)
                success = any(results)
            else:
                self.logger.info(f"All songs already exist for {playlist_config.name}")
                success = True

            # Update .spotdl file
            self._update_spotdl_file(playlist_config, spotify_url)

            return success

        except Exception as e:
            self.logger.error(f"Failed to sync playlist {playlist_config.name}: {e}")
            return False

    def _get_spotify_url(self, playlist_config: PlaylistConfig) -> Optional[str]:
        """Get Spotify URL from config or .spotdl file"""
        # Direct URL in config
        if playlist_config.spotify_url:
            return playlist_config.spotify_url

        # From .spotdl file
        if playlist_config.spotdl_file and playlist_config.spotdl_file.exists():
            return self.file_manager.load_spotdl_file(playlist_config.spotdl_file)

        # Search for .spotdl files in folder
        spotdl_files = list(playlist_config.folder_path.glob('*.spotdl'))
        if spotdl_files:
            return self.file_manager.load_spotdl_file(spotdl_files[0])

        self.logger.error(f"No Spotify URL found for {playlist_config.name}")
        return None

    def _filter_new_songs(self, songs: List[Song], folder_path: Path) -> List[Song]:
        """Filter out songs that already exist locally"""
        existing_songs = self.file_manager.get_existing_songs(folder_path)
        new_songs = []

        for song in songs:
            normalized_name = self.file_manager.normalize_song_name(song)
            if normalized_name not in existing_songs:
                new_songs.append(song)

        if new_songs:
            self.logger.info(f"Found {len(new_songs)} new songs to download")

        return new_songs

    def _update_spotdl_file(self, playlist_config: PlaylistConfig, spotify_url: str) -> None:
        """Update or create .spotdl file"""
        spotdl_file = playlist_config.folder_path / f"{playlist_config.name}.spotdl"
        self.file_manager.save_spotdl_file(spotify_url, spotdl_file)


class PlaylistManager:
    """Main playlist manager orchestrator"""

    DEFAULT_CONFIG_FILE = "~/.config/update_playlist/playlist.config"
    DEFAULT_LOG_FILE = "~/.cache/update_playlist/update_playlist.log"

    def __init__(self, config_path: str = None, log_file: str = None):
        """Initialize the playlist manager"""
        self.config_path = Path(config_path or self.DEFAULT_CONFIG_FILE).expanduser()
        self.log_file = Path(log_file or self.DEFAULT_LOG_FILE).expanduser()

        self.setup_logging()
        self.config_manager = ConfigManager(self.logger)
        self.file_manager = FileManager(self.logger)

        # Initialize components
        self.config = None
        self.spotdl_wrapper = None
        self.playlist_syncer = None

    def setup_logging(self) -> None:
        """Setup logging configuration"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> None:
        """Initialize all components"""
        # Create config if it doesn't exist
        if not self.config_path.exists():
            self.config_manager.create_default_config(self.config_path)
            self.logger.info("Created default configuration. Please edit it and run again.")
            return

        # Load configuration
        self.config = self.config_manager.load_config(self.config_path)

        # Initialize SpotDL wrapper
        self.spotdl_wrapper = SpotDLWrapper(
            client_id=self.config.spotify_client_id,
            client_secret=self.config.spotify_client_secret,
            audio_format=self.config.audio_format,
            audio_quality=self.config.audio_quality,
            logger=self.logger
        )

        # Initialize playlist syncer
        self.playlist_syncer = PlaylistSyncer(
            self.spotdl_wrapper,
            self.file_manager,
            self.logger
        )

    def sync_all_playlists(self, skip_sync: bool = False, force_resync: bool = False) -> None:
        """Sync all configured playlists"""
        if not self.config:
            raise RuntimeError("Manager not initialized")

        start_time = datetime.datetime.now()
        self.logger.info(f"Starting playlist update at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        success_count = 0
        total_count = len(self.config.playlists)

        for playlist_config in self.config.playlists:
            try:
                # Sync with Spotify
                if not skip_sync:
                    sync_success = self.playlist_syncer.sync_playlist(playlist_config, force_resync)
                    if not sync_success:
                        self.logger.warning(f"Sync failed for {playlist_config.name}")

                # Create M3U playlist
                self.file_manager.create_m3u_playlist(playlist_config.folder_path)
                success_count += 1

            except Exception as e:
                self.logger.error(f"Failed to process {playlist_config.name}: {e}")
                continue

        end_time = datetime.datetime.now()
        duration = end_time - start_time

        self.logger.info(f"Update completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Processed {success_count}/{total_count} playlists successfully")
        self.logger.info(f"Total duration: {duration}")

    def add_playlist(self, spotify_url: str, playlist_name: str) -> bool:
        """Add a new playlist from Spotify URL"""
        if not self.config:
            raise RuntimeError("Manager not initialized")

        try:
            folder_path = self.config.base_path / playlist_name

            # Create playlist config
            playlist_config = PlaylistConfig(
                name=playlist_name,
                folder_path=folder_path,
                spotify_url=spotify_url
            )

            # Sync the playlist
            success = self.playlist_syncer.sync_playlist(playlist_config)

            if success:
                # Add to config file
                with self.config_path.open('a', encoding='utf-8') as f:
                    f.write(f'{playlist_name} {spotify_url}\n')
                self.logger.info(f"Added {playlist_name} to configuration")

            return success

        except Exception as e:
            self.logger.error(f"Failed to add playlist {playlist_name}: {e}")
            return False
