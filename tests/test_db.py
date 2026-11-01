import pytest

from update_playlist import db


def test_add_list_remove():
    conn = db.connect(':memory:')
    db.add(conn, 'rock', 'https://open.spotify.com/playlist/b')
    db.add(conn, 'jazz', 'https://open.spotify.com/playlist/a')
    assert db.list_all(conn) == [('jazz', 'https://open.spotify.com/playlist/a'),
                                 ('rock', 'https://open.spotify.com/playlist/b')]

    with pytest.raises(ValueError, match='already exists'):
        db.add(conn, 'rock', 'https://x')
    for bad in ('', '..', 'a/b'):
        with pytest.raises(ValueError, match='Invalid'):
            db.add(conn, bad, 'https://x')

    assert db.remove(conn, 'rock') is True
    assert db.remove(conn, 'rock') is False
    assert [n for n, _ in db.list_all(conn)] == ['jazz']
