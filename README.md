# Update Playlist
Utility to manage playlist in subfolders, regurarly downloading new songs from a Spotify playlist. Using with Navidrome.

## Requirements & Usage

Since I have an externally managed python environment I setup dependencies in a virtual environment located in same base folder specified in the config file:

``` sh
base/
    playlist1/
    playlist2/
    e/ # virtual env
```

To create one and install dependencies in $BASE_DIRECTORY (define it yourself):
```
cd $BASE_DIRECTORY && python -m venv e && source e/bin/activate && pip install spotdl ffmpeg yt-dlp
```

## Automation

In `systemd` I put a template of service + timer to automate running the script in the background. Configure and then run:
```
cp systemd/update_playlist.service /etc/systemd/system/update_playlist.service && 
cp systemd/update_playlist.timer /etc/systemd/system/update_playlist.timer &&
systemd daemon-reload &&
systemd enable --now update_playlist.timer
```
