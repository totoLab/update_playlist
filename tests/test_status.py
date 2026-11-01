from update_playlist.main import sync_all
from update_playlist.web import Status


def test_sync_all_reports_per_playlist_state(tmp_path):
    (tmp_path / 'ok-list').mkdir()
    (tmp_path / 'ok-list' / 'a.mp3').touch()
    (tmp_path / 'broken').write_text('a file where the folder should be')
    status = Status()
    status.playlist('removed', state='ok')  # no longer in the DB: must disappear

    result = sync_all(None, [('ok-list', 'https://a'), ('broken', 'https://b')], tmp_path, status)

    s = status.snapshot()
    assert result == 1 and s['failed'] == 1 and not s['running'] and s['finished']
    assert set(s['playlists']) == {'ok-list', 'broken'}
    assert s['playlists']['ok-list']['files'] == 1
    assert s['playlists']['broken']['state'] == 'error' and s['playlists']['broken']['error']
