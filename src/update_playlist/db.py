import sqlite3
from pathlib import Path
from typing import List, Tuple


def connect(path: str) -> sqlite3.Connection:
    if path != ':memory:':
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE IF NOT EXISTS playlists ('
                 'name TEXT PRIMARY KEY, spotify_url TEXT NOT NULL)')
    return conn


def add(conn: sqlite3.Connection, name: str, spotify_url: str) -> None:
    # name becomes a folder under the music dir
    if not name or '/' in name or name in ('.', '..'):
        raise ValueError(f'Invalid playlist name: {name!r}')
    try:
        with conn:
            conn.execute('INSERT INTO playlists VALUES (?, ?)', (name, spotify_url))
    except sqlite3.IntegrityError:
        raise ValueError(f'Playlist already exists: {name}') from None


def remove(conn: sqlite3.Connection, name: str) -> bool:
    with conn:
        return conn.execute('DELETE FROM playlists WHERE name = ?', (name,)).rowcount > 0


def list_all(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    return conn.execute('SELECT name, spotify_url FROM playlists ORDER BY name').fetchall()
