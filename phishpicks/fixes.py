import os
import re
from typing import Union
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4Tags
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from pathlib import Path, WindowsPath
from tqdm import tqdm


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


def translate_to_m4(tags: dict) -> dict:
    return {
        '\xa9ART': tags['artist'],
        'aART': tags['albumartist'],
        '\xa9gen': tags['genre'],
        '\xa9day': tags['date'],
        'disk': tags['discnumber'],
        'trkn': tags['tracknumber'],
        '\xa9nam': tags['title'],
        '\xa9alb': tags['album'],
    }


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
        # print(track)
        if track.suffix in ['.mp3', '.MP3']:
            phish_dict = decompose_to_tag(track.name, venue=venue)
            audio = EasyID3()
            audio.update(phish_dict)
            audio.save(track)

        elif track.suffix in ['.m4a', '.M4a']:
            print(track)
            phish_dict = decompose_to_tag(track.name, venue=venue)
            audio = EasyMP4Tags()
            # audio.add_tags()
            print(type(audio))
            # audio.update(phish_dict)
            print(audio.items())
            audio.update(phish_dict)
            audio.save(track)

        elif track.suffix in ['.flac', '.FLAC']:
            print(track)
            phish_dict = decompose_to_tag(track.name, venue=venue)
            audio = FLAC(track)
            print(type(audio))


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
    elif re.compile(r'\d\d\d\d-\d\d-\d\d_.*').match(file_name):
        # e.g. 2016-07-15_The_Gorge_Amphitheatre_George_WA_ph160715d1__05_Bouncing_Around_The_Room.m4a
        track_match = r'__\d\d_(.*?)\.[mp3 flac m4a]'
        track_title = re.findall(track_match, file_name)[0]
        track_title = track_title.replace("_", " ")
        phish_dict = {
            "artist": artist,
            "albumartist": artist,
            "genre": "Rock",
            "date": file_name[0:4],
            "discnumber": file_name[53:54],
            "tracknumber": file_name[56:58],
            "title": track_title,
            "album": f"{file_name[:10]} {venue}",
        }
        return phish_dict
    elif re.compile(r'ph\d\d\d\d\d\dd\d_\d\d_.*'):
        # 07_23_16_Sleep_Train_Amphitheatre_Chula_Vista_CA_ph160723d1_07_Martian_Monster.m4a
        track_match = r'ph\d\d\d\d\d\dd\d_\d\d_(.*?)\.[mp3 flac m4a]'
        track_title = re.findall(track_match, file_name)[0]
        track_title = track_title.replace("_", " ")
        ph_match = r'_ph.*'
        ph_tag = re.findall(ph_match, file_name)[0]
        # _ph160723d1_01_Farmhouse.m4a
        year = ph_tag[3:5]
        year = f"19{year}" if year[0] in ['8', '9'] else f"20{year}"
        phish_dict = {
            "artist": artist,
            "albumartist": artist,
            "genre": "Rock",
            "date": year,
            "discnumber": ph_tag[10:11],
            "tracknumber": ph_tag[12:14],
            "title": track_title,
            "album": f"{year}-{ph_tag[5:7]}-{ph_tag[7:9]} {venue}",
        }
        return phish_dict


def read_tags(filename: Path):
    out_set = set()
    if filename.suffix == '.mp3':
        try:
            audio = EasyID3(filename)
            album = audio.get('album')
            if not album:
                out_set.add(filename.parent)
                print(filename.parent)
        except ID3NoHeaderError:
            out_set.add(filename.parent)
            print(filename.parent)
    elif filename.suffix == '.flac':
        try:
            audio = FLAC(filename)
            album = audio.get('album')
            if not album:
                out_set.add(filename.parent)
                print(filename.parent)
        except:
            out_set.add(filename.parent)
            print(filename.parent)
    elif filename.suffix == '.m4a':
        try:
            audio = MP4(filename)
            album = audio.get("\xa9alb")
            if not album:
                out_set.add(filename.parent)
                print(filename.parent)
        except:
            out_set.add(filename.parent)
            print(filename.parent)
    return out_set


def validate_tags(phish_folder: Path = Path("Z://Music//Phish")):
    out_set = set()
    tracks = [folder for folder in phish_folder.glob("Phish [0-9]*/*.[mp3 MP3 flac FLAC m4a M4A]*")]
    for track in tqdm(tracks):
        missing = read_tags(track)
        out_set.update(missing)
    return out_set


# out_set = validate_tags()
# print(out_set)

# fix_shows = [
#     WindowsPath('Z:/Music/Phish/Phish 1999-06-30 Verizon Wireless Amphitheater Kansas City Bonner Springs, KS, USA'),
#
# ]
# fix_missing_tags(str(fix_shows[0]), venue="Bonner Springs")
