import os
import sys
import logging
import argparse
from pathlib import Path

from . import db
from .sync import make_client, sync_playlist, write_m3u

log = logging.getLogger('update_playlist')


def env(name: str, default: str) -> str:
    return os.environ.get(name) or default


def setup_logging(log_file: str, verbose: bool) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        path = Path(log_file).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=handlers,
    )


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Download Spotify playlists and keep them in sync. '
                    'Spotify credentials are read from SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET.')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--add', nargs=2, metavar=('SPOTIFY_URL', 'NAME'), help='Add a playlist and sync it')
    actions.add_argument('--remove', metavar='NAME', help='Remove a playlist (downloaded files are kept)')
    actions.add_argument('--list', action='store_true', help='List playlists')

    parser.add_argument('--db', default=env('UPDATE_PLAYLIST_DB', '~/.local/share/update_playlist/playlists.db'),
                        help='SQLite database path [UPDATE_PLAYLIST_DB]')
    parser.add_argument('--music-dir', default=env('MUSIC_DIR', '~/Music/playlists'),
                        help='Folder where playlists are downloaded [MUSIC_DIR]')
    parser.add_argument('--format', default=env('AUDIO_FORMAT', 'mp3'), help='Audio format [AUDIO_FORMAT]')
    parser.add_argument('--bitrate', default=env('AUDIO_BITRATE', 'auto'),
                        help='Bitrate, e.g. auto, 320k [AUDIO_BITRATE]')
    parser.add_argument('--log-file', default=os.environ.get('UPDATE_PLAYLIST_LOG', '~/.cache/update_playlist/update_playlist.log'),
                        help='Log file, empty to disable [UPDATE_PLAYLIST_LOG]')
    parser.add_argument('--skip-sync', '-s', action='store_true', help='Only rebuild M3U files')
    parser.add_argument('--force-resync', '-f', action='store_true', help='Re-download all songs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging(args.log_file, args.verbose)
    conn = db.connect(str(Path(args.db).expanduser()))

    if args.list:
        for name, url in db.list_all(conn):
            print(f'{name}\t{url}')
        return 0

    if args.remove:
        if db.remove(conn, args.remove):
            log.info('Removed %s', args.remove)
            return 0
        log.error('No playlist named %s', args.remove)
        return 1

    if args.add:
        url, name = args.add
        try:
            db.add(conn, name, url)
        except ValueError as e:
            log.error('%s', e)
            return 1
        log.info('Added %s', name)
        playlists = [(name, url)]
    else:
        playlists = db.list_all(conn)
        if not playlists:
            log.info('No playlists yet. Add one with --add SPOTIFY_URL NAME')
            return 0

    music_dir = Path(args.music_dir).expanduser()
    client = None if args.skip_sync else make_client(
        os.environ.get('SPOTIFY_CLIENT_ID'), os.environ.get('SPOTIFY_CLIENT_SECRET'),
        args.format, args.bitrate, args.force_resync)

    ok = 0
    for name, url in playlists:
        folder = music_dir / name
        try:
            if client and not sync_playlist(client, url, folder):
                log.warning('Sync incomplete for %s', name)
            write_m3u(folder)
            ok += 1
        except Exception:
            log.exception('Failed to process %s', name)

    log.info('Processed %d/%d playlists', ok, len(playlists))
    return 0 if ok == len(playlists) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
