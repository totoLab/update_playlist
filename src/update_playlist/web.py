"""Status page: live sync state over a WebSocket, plus a button to start a sync."""
import asyncio
import copy
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from importlib.resources import files

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

log = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Status:
    """Sync state shared between the sync loop (writer) and WebSocket clients (readers)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.version = 0
        self._log = deque(maxlen=300)
        self._data = {
            'running': False,
            'current': None,
            'started': None,      # last run
            'finished': None,
            'failed': 0,          # playlists that errored in the last run
            'next_run': None,
            'playlists': {},      # name -> {url, state, present, total, files, synced, error}
        }

    def update(self, **fields) -> None:
        with self._lock:
            self._data.update(fields)
            self.version += 1

    def playlist(self, name: str, **fields) -> None:
        with self._lock:
            self._data['playlists'].setdefault(name, {}).update(fields)
            self.version += 1

    def reset_playlists(self, playlists) -> None:
        """Keep previous results for playlists still in the DB, drop removed ones."""
        with self._lock:
            old = self._data['playlists']
            self._data['playlists'] = {n: {**old.get(n, {'state': 'pending'}), 'url': u} for n, u in playlists}
            self.version += 1

    def add_log(self, line: str) -> None:
        with self._lock:
            self._log.append(line)
            self.version += 1

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


def make_app(status: Status, trigger: threading.Event) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    page = files(__package__).joinpath('status.html').read_text(encoding='utf-8')

    @app.get('/', response_class=HTMLResponse)
    def index():
        return page

    @app.websocket('/ws')
    async def ws(websocket: WebSocket):
        await websocket.accept()

        async def receive():
            while True:
                msg = await websocket.receive_json()
                if msg.get('action') == 'sync' and not status.snapshot()['running']:
                    status.update(running=True, current=None)  # show it at once, block double clicks
                    log.info('Manual sync requested from the status page')
                    trigger.set()

        receiver = asyncio.create_task(receive())
        sent = -1
        try:
            # ponytail: polls the version every 0.5s instead of pushing from the sync thread;
            # fine for a handful of viewers, switch to call_soon_threadsafe fan-out if that grows
            while not receiver.done():
                if status.version != sent:
                    sent = status.version
                    await websocket.send_json(status.snapshot())
                await asyncio.sleep(0.5)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            receiver.cancel()

    return app


def start(host: str, port: int, status: Status, trigger: threading.Event) -> None:
    """Serve the status page from a daemon thread; the sync loop keeps the main thread."""
    logging.getLogger().addHandler(StatusLogHandler(status))
    config = uvicorn.Config(make_app(status, trigger), host=host, port=port, log_level='warning')
    threading.Thread(target=uvicorn.Server(config).run, daemon=True, name='status-page').start()
    log.info('Status page on http://%s:%d', host, port)
