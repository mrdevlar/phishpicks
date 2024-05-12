import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from pydub import AudioSegment
from mutagen.easymp4 import EasyMP4Tags


def track_dict(path, name, album, tracknumber, artist):
    return {
        'path': path,
        'name': name,
        'album': album,
        'tracknumber': tracknumber,
        'artist': artist
    }


def make_flac(track_dict: dict):
    silent_segment = AudioSegment.silent(duration=2000)
    file_path = Path(track_dict['path']) / f"{track_dict['tracknumber']} {track_dict['name']}.flac"
    silent_segment.export(file_path, format="flac", tags={
        "title": track_dict['name'],
        "artist": track_dict['artist'],
        "album": track_dict['album'],
        "tracknumber": track_dict['tracknumber'],
    })


def make_mp3(track_dict: dict):
    silent_segment = AudioSegment.silent(duration=1000)
    file_path = Path(track_dict['path']) / f"{track_dict['tracknumber']} {track_dict['name']}.mp3"
    silent_segment.export(file_path, format="mp3", tags={
        'TIT2': track_dict['name'],
        'TPE1': track_dict['artist'],
        'TALB': track_dict['album'],
        'TRCK': track_dict['tracknumber'],
    })



def make_m4a(path):
    silent_segment = AudioSegment.silent(duration=1000)
    file_path = Path(path) / "03 Sand.m4a"
    # AudioSegment tags don't work for mp4
    silent_segment.export(file_path, format="mp4")
    new_tags = {
        "artist": "Phish",
        "albumartist": "Phish",
        "genre": "Rock",
        "date": "2024",
        "discnumber": "1",
        "tracknumber": "3",
        "title": "Sand",
        "album": "2024-01-01 Imaginary Venue You Keep Within Your Head",
    }
    audio = EasyMP4Tags()
    audio.update(new_tags)
    audio.save(file_path)


@pytest.fixture(scope="session", autouse=True)
def settings():
    with TemporaryDirectory() as tempdir:
        config_folder = Path(tempdir) / Path(".testpicks")
        phish_folder = Path(tempdir) / Path("PhishTest")
        phish_folder.mkdir(parents=True)
        media_player_path = Path(tempdir) / Path('winamp.exe')
        media_player_path.touch()
        # @TODO: Replace with arbitrary folder generator
        album1 = "2024-01-01 Imaginary Venue You Keep Within Your Head"
        show = phish_folder / Path(album1)
        show.mkdir(parents=True)
        make_flac(track_dict(show, "Ghost", show, "1", "Phish"))
        make_mp3(track_dict(show, "Everything's Right", show, "2", "Phish"))
        album2 = "2024-01-02 Also Not a Venue"
        show2 = phish_folder / Path(album2)
        show2.mkdir(parents=True)
        make_m4a(show2)
        # Return a dict
        yield {
            'tempdir': tempdir,
            'config_file': "phishtestpicks.json",
            'config_folder': str(Path(config_folder)),
            'phish_folder': str(Path(phish_folder)),
            'shows': [show, show2],
            'phish_db': "phish.db",
            'show_glob': "[0-9]*",
            'venue_regex': r'\d\d\d\d-\d\d-\d\d (.*?.*)',
            'media_player_path': str(Path(media_player_path))
        }
