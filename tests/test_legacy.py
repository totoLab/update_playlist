import json
from pathlib import Path

from update_playlist import db, legacy


def test_migrate_both_formats_and_spotdl_files(tmp_path, monkeypatch):
    home, data, music = tmp_path / 'home', tmp_path / 'data', tmp_path / 'music'
    monkeypatch.setattr(Path, 'home', lambda: home)

    # INI-style text in ~/.config, base points at the music dir
    cfg = home / '.config' / 'update_playlist' / 'playlist.config'
    cfg.parent.mkdir(parents=True)
    cfg.write_text(f'# comment\n[base]\n{music}\n\n[playlists]\n'
                   'inline https://open.spotify.com/playlist/inline\n'
                   'sync-file\nsave-file\nold-app\nno-url\n')
    for name, content in [
        ('sync-file', {'type': 'sync', 'query': ['https://open.spotify.com/playlist/sync'], 'songs': []}),
        ('save-file', [{'name': 'x', 'list_url': 'https://open.spotify.com/playlist/save'}]),
        ('old-app', {'query': 'https://open.spotify.com/playlist/old', 'format': 'json'}),
    ]:
        (music / name).mkdir(parents=True)
        (music / name / f'{name}.spotdl').write_text(json.dumps(content))

    # 0.2.x JSON next to the DB (Docker case), with a duplicate name that must be skipped
    data.mkdir()
    (data / 'playlist.json').write_text(json.dumps({
        'base_path': str(music),
        'playlists': [{'name': 'json-one', 'spotify_url': 'https://open.spotify.com/playlist/json'},
                      {'name': 'inline', 'spotify_url': 'https://dup'}],
    }))

    conn = db.connect(':memory:')
    assert legacy.migrate(conn, data, music) == 5
    assert dict(db.list_all(conn)) == {
        'inline': 'https://open.spotify.com/playlist/inline',
        'sync-file': 'https://open.spotify.com/playlist/sync',
        'save-file': 'https://open.spotify.com/playlist/save',
        'old-app': 'https://open.spotify.com/playlist/old',
        'json-one': 'https://open.spotify.com/playlist/json',
    }


def test_garbage_file_does_not_block_startup(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    (tmp_path / 'playlist.json').write_text('{"playlists": [{"no_name": 1}]}')
    assert legacy.migrate(db.connect(':memory:'), tmp_path, tmp_path) == 0


def test_old_cron_config_path(tmp_path, monkeypatch):
    # cron used: update-playlist --config ~/.config/playlist_manager/config.json
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    cfg = tmp_path / '.config' / 'playlist_manager' / 'config.json'
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({'base_path': str(tmp_path),
                               'playlists': [{'name': 'a', 'spotify_url': 'https://open.spotify.com/playlist/a'}]}))
    conn = db.connect(':memory:')
    assert legacy.migrate(conn, tmp_path / 'data', tmp_path) == 1
    assert [n for n, _ in db.list_all(conn)] == ['a']


def test_folder_warning_only_when_old_songs_not_visible(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    data, music = tmp_path / 'data', tmp_path / 'music'
    data.mkdir()
    (data / 'playlist.json').write_text(json.dumps({
        'base_path': '/home/someone/library/music',  # host path, as seen from inside Docker
        'playlists': [{'name': 'p', 'spotify_url': 'https://open.spotify.com/playlist/p'}]}))

    legacy.migrate(db.connect(':memory:'), data, music)
    assert 'point MUSIC_DIR' in caplog.text

    caplog.clear()
    (music / 'p').mkdir(parents=True)  # old folder mounted at MUSIC_DIR
    legacy.migrate(db.connect(':memory:'), data, music)
    assert 'point MUSIC_DIR' not in caplog.text
