import os
import re
from typing import Union
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
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


def fix_missing_tags(folder: Union[os.PathLike, Path, str],
                     venue: str = None,
                     phish_folder: Path = Path("Z://Music//Phish")) -> None:
    """
    Uses the file information to fix the tags of a Phish show
    Args:
        folder: Phish show folder
        venue: Venue of the Phish show
        phish_folder: Root Phish folder
    """
    show_folder = Path(phish_folder) / Path(folder)
    if not show_folder.exists():
        raise FileNotFoundError(f"Folder Does Not Exists: {show_folder}")
    print(show_folder)
    tracks = list(show_folder.glob("*.[mp3 MP3 flac FLAC m4a M4A]*"))
    for track in tracks:
        if track.suffix in ['.mp3', '.MP3']:
            phish_dict = decompose_to_tag(track.name, venue=venue)
            audio = EasyID3()
            audio.update(phish_dict)
            print(audio)
            audio.save(track)


def decompose_to_tag(file_path: str, venue: str = None) -> dict:
    """
    Decomposes a Phish file name into a tag
    Args:
        file_path: Path of the Phish show
        venue: Venue of the Phish show

    Returns:
        Dictionary of mp3/flac tags
    """
    file_path = Path(file_path)
    file_name = file_path.name
    print(file_name)
    artist = "Phish"
    if re.compile(r'^ph\d\d\d\d\d\dd\d_\d\d_.*').match(file_name):
        # e.g. ph030221d1_03_Down_With_Disease.mp3
        track_match = r'^ph\d\d\d\d\d\dd\d_\d\d_(.*?)\.[mp3 flac m4a]'
        track_title = re.findall(track_match, file_name)[0]
        track_title = track_title.replace("_", " ")
        year = file_name[2:4]
        year = f"19{year}" if year[0] in ['8', '9'] else f"20{year}"

        phish_dict = {
            "artist": artist,
            "albumartist": artist,
            "genre": "Rock",
            "date": year,
            "discnumber": file_name[9:10],
            "tracknumber": file_name[11:13],
            "title": track_title,
            "album": f"{year}-{file_name[4:6]}-{file_name[6:8]} {venue}",
        }
        return phish_dict


def read_tags(filename: Path):
    try:
        audio = EasyID3(filename)
    except ID3NoHeaderError:
        print(filename)
