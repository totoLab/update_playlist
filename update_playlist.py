import os, sys, subprocess, datetime, re, argparse, shutil

DEFAULT_LOG_FILE = "~/.cache/update_playlist/update_playlist.log"

def log(msg, log_file=DEFAULT_LOG_FILE):
    log_file=os.path.expanduser(log_file)
    log_message = f"INFO: {msg}\n"
    print(log_message, end="")
    with open(log_file, "a") as f:
        f.write(log_message)

def error(msg, log_file=DEFAULT_LOG_FILE):
    log_file=os.path.expanduser(log_file)
    log_message = f"ERROR: {msg}\n"
    print(log_message, end="")
    with open(log_file, "a") as f:
        f.write(log_message)
    sys.exit(1)

def create_m3u_from_folder(folder_path, output_m3u):
    # Supported media file extensions
    media_extensions = {'.mp3', '.mp4', '.mkv', '.avi', '.flac', '.wav', '.aac', '.ogg', 'opus'}
    
    media_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in media_extensions):
                media_files.append(os.path.basename(file))
    
    # Write the playlist file
    with open(output_m3u, 'w') as m3u_file:
        for media_file in media_files:
            m3u_file.write(media_file + '\n')
    
    log(f'M3U playlist created: {output_m3u}')

def update(config, skip_sync=False):
    base, folders = config["base"][0], config["playlists"]
    now = datetime.datetime.now()
    log(f"Starting update {now.strftime("%Y-%m-%d %H:%M:%S")} of library located in {base}")
    for folder in folders:
        folder_path = os.path.join(base, folder)
        if not os.path.exists(folder_path):
            log(f"Folder does not exist: {folder_path}")
            continue
        
        try:
            if not skip_sync:
                log(f"Processing folder {folder_path}...")
                if any(File.endswith(".spotdl") for File in os.listdir(folder_path)):
                    command = f"cd {folder_path} && source {os.path.join(base, "e/bin/activate")} && spotdl sync {folder_path}/*.spotdl --sync-without-deleting"
                    log("Updating songs...")
                    subprocess.run(command, shell=True, check=True, executable="/usr/bin/zsh")
                else:
                    log("Couldn\'t find a playlist to download, set it up with \"spotdl \'http://open.spotify.com/...\' --save-file myplaylist.spotdl\" first.")
                
            output_m3u = f"{os.path.basename(folder_path.rstrip('/'))}.m3u"
            log(f"Updating playlist {output_m3u}")
            path_output_m3u = os.path.join(folder_path, output_m3u)
            create_m3u_from_folder(folder_path, path_output_m3u)

        except subprocess.CalledProcessError as e:
            log(f"'Couln't update {os.path.basename(folder_path)} correctly': {e}")
            continue

    now = datetime.datetime.now()
    log(f"Update finished {now.strftime("%Y-%m-%d %H:%M:%S")}\n")

def parse_config(path):
    config = {}
    title_regex = re.compile(r"\[([a-zA-Z0-9]+)\]")
    with open(path, "r") as f:
        content = f.read()

        current_title = None
        for line in content.splitlines():
            line = line.strip()
            if line == '': 
                current_title = None
                continue

            result = title_regex.search(line)
            if result is not None:
                title = result.group(1)
                current_title = title
                if current_title not in config:
                    config[current_title] = []
            else:
                if current_title is None:
                    error("Bad config")
                if not line.startswith("#"):
                    config[current_title].append(line)

    return config

def setup(config_file_path):
    def get_path(filepath):
        return os.path.dirname(filepath)

    directories = [
        get_path(config_file_path),
        get_path(DEFAULT_LOG_FILE)
    ]

    for dir in directories:
        if not os.path.exists(dir):
            log(f"Creating missing directory {dir}")
            os.makedirs(dir)

    installer_path = get_path(os.path.realpath(__file__))
    if not os.path.exists(config_file_path):
        log(f"Config file doesn't exist in {config_file_path}, creating a new one with a template.")
        shutil.copy(
            os.path.join(installer_path, "playlist.config"),
            config_file_path
        )

def main(config_file="~/.config/update_playlist/playlist.config", skip_sync=False):
    setup(config_file)
    config_file_path = os.path.expanduser(config_file)
    configuration = parse_config(config_file_path)
    
    update(configuration, skip_sync)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-sync', action='store_true')
    args = parser.parse_args()
    main(skip_sync=args.skip_sync)
