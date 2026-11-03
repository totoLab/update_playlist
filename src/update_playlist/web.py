"""Status page: live sync state pushed over Server-Sent Events, plus buttons to add a playlist and start a sync."""
import asyncio
import copy
import json
import logging
import threading
from collections import deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Optional
from importlib.resources import files

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import db

log = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def next_run(hours: Optional[float], since: Optional[str] = None) -> Optional[str]:
    if not hours:
        return None
    start = datetime.fromisoformat(since) if since else datetime.now(timezone.utc)
    return (start + timedelta(hours=hours)).isoformat(timespec='seconds')


class Status:
    """Sync state shared between the sync loop (writer) and SSE clients (readers)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._listeners = set()  # callables run on every change, from any thread
        self._log = deque(maxlen=300)
        self._data = {
            'running': False,
            'current': None,
            'started': None,      # last run
            'finished': None,
            'failed': 0,          # playlists that errored in the last run
            'next_run': None,
            'interval': None,     # hours between syncs, None = manual only
            'playlists': {},      # name -> {url, state, present, total, files, synced, error}
        }

    def _notify(self) -> None:
        for wake in self._listeners:
            wake()

    def subscribe(self, wake) -> None:
        with self._lock:
            self._listeners.add(wake)

    def unsubscribe(self, wake) -> None:
        with self._lock:
            self._listeners.discard(wake)

    def update(self, **fields) -> None:
        with self._lock:
            self._data.update(fields)
            self._notify()

    def playlist(self, name: str, **fields) -> None:
        with self._lock:
            self._data['playlists'].setdefault(name, {}).update(fields)
            self._notify()

    def reset_playlists(self, playlists) -> None:
        """Keep previous results for playlists still in the DB, drop removed ones."""
        with self._lock:
            old = self._data['playlists']
            self._data['playlists'] = {n: {**old.get(n, {'state': 'pending'}), 'url': u} for n, u in playlists}
            self._notify()

    def add_log(self, line: str) -> None:
        with self._lock:
            self._log.append(line)
            self._notify()

    def snapshot(self) -> dict:
        with self._lock:
            return {**copy.deepcopy(self._data), 'log': list(self._log), 'now': now()}


class StatusLogHandler(logging.Handler):
    def __init__(self, status: Status):
        super().__init__(logging.INFO)
        self.status = status
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S'))

    def emit(self, record):
        self.status.add_log(self.format(record))


class Interval(BaseModel):
    hours: float = Field(ge=0, le=24 * 365)  # 0 = manual only


class NewPlaylist(BaseModel):
    name: str
    url: str


def make_app(status: Status, trigger: threading.Event, db_path: str) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    page = files(__package__).joinpath('status.html').read_text(encoding='utf-8')

    @app.get('/', response_class=HTMLResponse)
    def index():
        return page

    @app.get('/events')
    async def events():
        loop = asyncio.get_running_loop()
        changed = asyncio.Event()

        def wake():
            loop.call_soon_threadsafe(changed.set)

        async def stream():
            status.subscribe(wake)
            try:
                while True:
                    changed.clear()  # before the snapshot, so a change in between isn't lost
                    yield f'data: {json.dumps(status.snapshot())}\n\n'
                    await changed.wait()
            finally:
                status.unsubscribe(wake)

        return StreamingResponse(stream(), media_type='text/event-stream')

    @app.post('/sync', status_code=204)
    def sync():
        if not status.snapshot()['running']:
            status.update(running=True, current=None)  # show it at once, block double clicks
            log.info('Manual sync requested from the status page')
            trigger.set()

    @app.put('/interval', status_code=204)
    def set_interval(body: Interval):
        hours = body.hours or None
        with closing(db.connect(db_path)) as conn:
            db.set_setting(conn, 'interval', str(body.hours))
        s = status.snapshot()
        # while running, the sync loop schedules the next run itself when it finishes
        fields = {} if s['running'] else {'next_run': next_run(hours, s['finished'])}
        status.update(interval=hours, **fields)
        log.info('Sync interval set to %s from the status page', f'{hours:g} hours' if hours else 'manual only')

    @app.post('/playlists', status_code=201)
    def add_playlist(body: NewPlaylist):
        name, url = body.name.strip(), body.url.strip()
        try:
            with closing(db.connect(db_path)) as conn:  # sqlite connections can't cross threads
                db.add(conn, name, url)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        log.info('Added %s from the status page', name)
        status.playlist(name, state='pending', url=url)
        trigger.set()  # if a sync is running, one more run follows it

    return app


def start(host: str, port: int, status: Status, trigger: threading.Event, db_path: str) -> None:
    """Serve the status page from a daemon thread; the sync loop keeps the main thread."""
    logging.getLogger().addHandler(StatusLogHandler(status))
    config = uvicorn.Config(make_app(status, trigger, db_path), host=host, port=port, log_level='warning')
    threading.Thread(target=uvicorn.Server(config).run, daemon=True, name='status-page').start()
    log.info('Status page on http://%s:%d', host, port)
