import logging
from pathlib import Path

from spotdl import Spotdl
from spotdl.utils.config import DEFAULT_CONFIG
from spotdl.utils.formatter import create_file_name

log = logging.getLogger(__name__)

MEDIA_EXTENSIONS = {'.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg', '.opus'}


def make_client(client_id=None, client_secret=None, audio_format='mp3',
                bitrate='auto', force=False) -> Spotdl:
    """Create the spotdl client. Only one per process: spotdl's Spotify client is a singleton."""
    return Spotdl(
        client_id=client_id or DEFAULT_CONFIG['client_id'],
        client_secret=client_secret or DEFAULT_CONFIG['client_secret'],
        headless=True,
        downloader_settings={
            'format': audio_format,
            'bitrate': bitrate,
            # spotdl checks for the file before searching YouTube, so "skip" makes reruns cheap
            'overwrite': 'force' if force else 'skip',
        },
    )


def sync_playlist(client: Spotdl, spotify_url: str, folder: Path) -> bool:
    """Download missing songs of a Spotify URL into folder. True if every song is present."""
    folder.mkdir(parents=True, exist_ok=True)
    client.downloader.settings['output'] = str(folder / '{artists} - {title}.{output-ext}')

    songs = client.search([spotify_url])
    if not songs:
        log.warning('No songs found for %s', spotify_url)
        return False

    settings = client.downloader.settings
    if settings['overwrite'] == 'skip':
        # spotdl re-fetches each song's metadata from Spotify before checking the file; check first
        todo = [s for s in songs if not create_file_name(
            song=s, template=settings['output'], file_extension=settings['format'],
            restrict=settings['restrict'], file_name_length=settings['max_filename_length']).exists()]
    else:
        todo = songs

    present = len(songs) - len(todo)
    if todo:
        present += sum(path is not None for _, path in client.download_songs(todo))
    log.info('%s: %d/%d songs present', folder.name, present, len(songs))
    return present == len(songs)


def write_m3u(folder: Path) -> Path:
    """Write <folder>/<folder>.m3u listing every media file, relative paths, sorted."""
    folder.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in folder.rglob('*')
                   if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS)
    output = folder / f'{folder.name}.m3u'
    lines = ['#EXTM3U', *(str(p.relative_to(folder)) for p in files)]
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    log.info('Wrote %s (%d files)', output, len(files))
    return output
