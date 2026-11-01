import sys
import logging
import argparse
from pathlib import Path

from . import config as cfg
from .sync import make_client, sync_playlist, write_m3u

DEFAULT_CONFIG_FILE = '~/.config/update_playlist/playlist.json'
DEFAULT_LOG_FILE = '~/.cache/update_playlist/update_playlist.log'

log = logging.getLogger('update_playlist')


def setup_logging(log_file: Path, verbose: bool) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Spotify playlist downloader')
    parser.add_argument('--config', '-c', default=DEFAULT_CONFIG_FILE, help='Configuration file path')
    parser.add_argument('--log-file', '-l', default=DEFAULT_LOG_FILE, help='Log file path')
    parser.add_argument('--skip-sync', '-s', action='store_true', help='Only rebuild M3U files')
    parser.add_argument('--force-resync', '-f', action='store_true', help='Re-download all songs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--add-playlist', nargs=2, metavar=('SPOTIFY_URL', 'NAME'), help='Add new playlist')
    args = parser.parse_args()

    setup_logging(Path(args.log_file).expanduser(), args.verbose)
    config_path = Path(args.config).expanduser()

    if not config_path.exists():
        cfg.create_default_config(config_path)
        log.info('Created default configuration at %s. Edit it and run again.', config_path)
        return 0

    config = cfg.load_config(config_path)
    if args.add_playlist:
        url, name = args.add_playlist
        playlists = [cfg.PlaylistConfig(name, config.base_path / name, url)]
    else:
        playlists = config.playlists

    client = None if args.skip_sync else make_client(
        config.spotify_client_id, config.spotify_client_secret,
        config.audio_format, config.bitrate, args.force_resync)

    ok = 0
    for p in playlists:
        try:
            if client and p.spotify_url and not sync_playlist(client, p.spotify_url, p.folder_path):
                log.warning('Sync incomplete for %s', p.name)
            write_m3u(p.folder_path)
            ok += 1
        except Exception:
            log.exception('Failed to process %s', p.name)

    if args.add_playlist and ok:
        cfg.add_playlist(config_path, name, url)
        log.info('Added %s to %s', name, config_path)

    log.info('Processed %d/%d playlists', ok, len(playlists))
    return 0 if ok == len(playlists) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
