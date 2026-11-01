import os
import sys
import threading
import logging
import argparse
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import db, legacy, web
from .web import Status, now
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
    parser.add_argument('--interval', type=float, metavar='HOURS',
                        help='Keep running and sync every HOURS hours')
    parser.add_argument('--web', type=int, metavar='PORT', default=os.environ.get('WEB_PORT') or None,
                        help='Keep running and serve a status page on PORT [WEB_PORT]')
    parser.add_argument('--web-host', default=env('WEB_HOST', '127.0.0.1'),
                        help='Address for the status page [WEB_HOST]')
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging(args.log_file, args.verbose)
    db_path = Path(args.db).expanduser()
    music_dir = Path(args.music_dir).expanduser()
    new_db = not db_path.exists()
    try:
        conn = db.connect(str(db_path))
    except (sqlite3.Error, OSError) as e:
        log.error('Cannot open database %s: %s (is its folder writable by uid %d?)', db_path, e, os.getuid())
        return 1
    if new_db:
        # only on first start, so playlists removed later aren't re-imported
        legacy.migrate(conn, db_path.parent, music_dir)

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

    client = None if args.skip_sync else make_client(
        os.environ.get('SPOTIFY_CLIENT_ID'), os.environ.get('SPOTIFY_CLIENT_SECRET'),
        args.format, args.bitrate, args.force_resync)

    status = Status()
    if args.add:
        return sync_all(client, [(name, url)], music_dir, status)

    trigger = threading.Event()  # set by the status page's "Sync now" button
    if args.web:
        web.start(args.web_host, args.web, status, trigger)

    while True:
        # re-read the DB each run so playlists added meanwhile are picked up
        result = sync_all(client, db.list_all(conn), music_dir, status)
        if not args.interval and not args.web:
            return result
        timeout = args.interval * 3600 if args.interval else None
        if timeout:
            next_run = datetime.now(timezone.utc) + timedelta(seconds=timeout)
            status.update(next_run=next_run.isoformat(timespec='seconds'))
            log.info('Next sync in %g hours', args.interval)
        trigger.wait(timeout)
        trigger.clear()


def sync_all(client, playlists, music_dir: Path, status: Status) -> int:
    status.reset_playlists(playlists)
    status.update(running=True, current=None, started=now(), next_run=None)
    if not playlists:
        log.info('No playlists yet. Add one with --add SPOTIFY_URL NAME')

    failed = 0
    for name, url in playlists:
        folder = music_dir / name
        status.update(current=name)
        status.playlist(name, state='syncing', error=None)
        try:
            present = total = None
            if client:
                present, total = sync_playlist(client, url, folder)
                if present < total or not total:
                    log.warning('Sync incomplete for %s', name)
            files = write_m3u(folder)
            state = 'ok' if present == total and total != 0 else 'incomplete'
            status.playlist(name, state=state, present=present, total=total, files=files, synced=now())
        except Exception as e:
            failed += 1
            log.exception('Failed to process %s', name)
            status.playlist(name, state='error', error=str(e) or type(e).__name__)

    status.update(running=False, current=None, finished=now(), failed=failed)
    log.info('Processed %d/%d playlists', len(playlists) - failed, len(playlists))
    return 1 if failed else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
