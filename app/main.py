import sys
import logging
import argparse

from .playlist import PlaylistManager


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description="Modular Spotify Playlist Manager")
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--log-file', '-l', help='Log file path')
    parser.add_argument('--skip-sync', '-s', action='store_true', help='Skip Spotify sync')
    parser.add_argument('--force-resync', '-f', action='store_true', help='Force re-download all songs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--add-playlist', nargs=2, metavar=('SPOTIFY_URL', 'NAME'),
                       help='Add new playlist')

    args = parser.parse_args()

    try:
        # Initialize manager
        manager = PlaylistManager(args.config, args.log_file)

        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        manager.initialize()

        # Handle adding new playlist
        if args.add_playlist:
            spotify_url, name = args.add_playlist
            success = manager.add_playlist(spotify_url, name)
            sys.exit(0 if success else 1)

        # Check if config was just created
        if not manager.config:
            sys.exit(0)

        # Sync all playlists
        manager.sync_all_playlists(args.skip_sync, args.force_resync)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
