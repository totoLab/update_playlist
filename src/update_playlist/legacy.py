"""One-time import of playlists from the config files of earlier versions.

Two formats were used, both usually at ~/.config/update_playlist/playlist.config:
- INI-like text:  [base] <path>  /  [playlists] <name> [<url>]
- JSON (0.2.x):   {"base_path": ..., "playlists": [{"name": ..., "spotify_url": ...}]}
Playlists without a URL had it in a <base>/<name>/*.spotdl file.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

from . import db

log = logging.getLogger(__name__)

FILE_NAMES = ('playlist.config', 'playlist.json')

Entries = List[Tuple[str, Optional[str]]]


def candidates(db_dir: Path) -> List[Path]:
    # db_dir covers Docker, where ~/.config isn't mounted: drop the old file next to the DB
    dirs = [Path.home() / '.config' / 'update_playlist', db_dir]
    paths = [d / n for d in dirs for n in FILE_NAMES]
    # used by cron setups: update-playlist --config ~/.config/playlist_manager/config.json
    paths.append(Path.home() / '.config' / 'playlist_manager' / 'config.json')
    return paths


def parse(text: str) -> Tuple[Optional[str], Entries]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return parse_ini(text)
    base = data.get('base_path')
    entries = [(p['name'], p.get('spotify_url')) for p in data.get('playlists', [])]
    return base, entries


def parse_ini(text: str) -> Tuple[Optional[str], Entries]:
    section, base, entries = None, None, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
        elif section == 'base' and base is None:
            base = line
        elif section == 'playlists':
            name, _, url = line.partition(' ')
            url = url.strip()
            entries.append((name, url) if url.startswith(('http://', 'https://')) else (line, None))
    return base, entries


def url_from_spotdl_files(folder: Path) -> Optional[str]:
    """Find the Spotify URL in any .spotdl file format spotdl or this app ever wrote."""
    for f in sorted(folder.glob('*.spotdl')):
        try:
            text = f.read_text(encoding='utf-8').strip()
        except OSError:
            continue
        if text.startswith('http'):
            return text
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        url = None
        if isinstance(data, dict):  # spotdl sync file ({"query": [url]}) or 0.2.x ({"query": url})
            url = data.get('query') or data.get('url')
            if isinstance(url, list):
                url = url[0] if url else None
        elif isinstance(data, list) and data and isinstance(data[0], dict):  # spotdl --save-file
            url = data[0].get('list_url')
        if isinstance(url, str) and url.startswith('http'):
            return url
    return None


def migrate(conn: sqlite3.Connection, db_dir: Path, music_dir: Path) -> int:
    """Import playlists from any legacy config found. Returns how many were added."""
    total = 0
    for path in candidates(db_dir):
        if not path.is_file():
            continue
        try:
            base, entries = parse(path.read_text(encoding='utf-8'))
        except Exception as e:
            log.warning('Could not read legacy config %s: %s', path, e)
            continue

        base_dir = Path(base).expanduser() if base else music_dir
        for name, url in entries:
            # in Docker the old base path doesn't exist; the old folder is mounted at MUSIC_DIR
            url = url or url_from_spotdl_files(base_dir / name) or url_from_spotdl_files(music_dir / name)
            if not url:
                log.warning('Not importing %s: no Spotify URL in %s or its .spotdl files', name, path)
                continue
            try:
                db.add(conn, name, url)
                total += 1
            except ValueError as e:
                log.warning('Not importing %s: %s', name, e)

        log.info('Imported playlists from legacy config %s', path)
        if base and base_dir.resolve() != music_dir.resolve():
            log.warning('Legacy config downloaded to %s, now MUSIC_DIR is %s. To reuse the songs '
                        'already there, point MUSIC_DIR (in Docker: MUSIC_HOST_DIR) at %s',
                        base, music_dir, base)
    return total
