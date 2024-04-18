import os
import re
from typing import Union
from mutagen.easyid3 import EasyID3
from pathlib import Path


# @TODO: Fix tags if not consistent among entire show

def fix_folder_venue(folder: Union[os.PathLike, Path, str], phish_folder: Path = Path("Z://Music//Phish")) -> None:
    """
    Renames a Phish show folder with venue from tag
    Args:
        folder: Phish folder to fix
        phish_folder: Root phish folder
    """
    show_folder = Path(phish_folder) / Path(folder)
    if not show_folder.exists():
        raise FileNotFoundError(f"Folder Does Not Exists: {show_folder}")
    print(show_folder)
    first_track = next(show_folder.glob("*.[mp3 MP3 flac FLAC m4a M4A]*"))
    if first_track.suffix in ['.mp3', '.MP3']:
        audio = EasyID3(first_track)
        album = audio["album"][0]
        print(f"{album}")
        pattern = re.compile(r'^\d\d\d\d.*')
        if pattern.match(album):
            album = f"Phish {album}"
            new_show_folder = phish_folder / album
            os.rename(show_folder, new_show_folder)
            print(f"Renamed {show_folder} to {new_show_folder}")
        else:
            raise Exception("Album is wrong format")
