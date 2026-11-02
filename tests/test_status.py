import json
import socket
import threading
import time
import urllib.error
import urllib.request

from update_playlist import web
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


def test_add_playlist_from_page(tmp_path):
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    trigger = threading.Event()
    status = Status()
    web.start('127.0.0.1', port, status, trigger, str(tmp_path / 'p.db'))

    def post(name):
        req = urllib.request.Request(f'http://127.0.0.1:{port}/playlists', method='POST',
                                     data=json.dumps({'name': name, 'url': 'https://x'}).encode(),
                                     headers={'Content-Type': 'application/json'})
        for _ in range(50):  # the server thread needs a moment to listen
            try:
                return urllib.request.urlopen(req).status
            except urllib.error.HTTPError as e:
                return e.code
            except urllib.error.URLError:
                time.sleep(0.1)

    assert post('a') == 201
    assert trigger.is_set() and status.snapshot()['playlists']['a']['state'] == 'pending'
    assert post('a') == 400
    assert post('../x') == 400
