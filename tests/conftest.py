import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from pydub import AudioSegment
from mutagen.easymp4 import EasyMP4Tags


def make_flac(path):
    silent_segment = AudioSegment.silent(duration=2000)
    file_path = Path(path) / "01 Ghost.flac"
    silent_segment.export(file_path, format="flac", tags={
        "title": "Ghost",
        "artist": "Phish",
        "album": "2024-01-01 Imaginary Venue You Keep Within Your Head",
        "tracknumber": "1",
    })


def make_mp3(path):
    silent_segment = AudioSegment.silent(duration=1000)
    file_path = Path(path) / "02 Everything's Right.mp3"
    silent_segment.export(file_path, format="mp3", tags={
        'TIT2': "Everything's Right",
        'TPE1': "Phish",
        'TALB': "2024-01-01 Imaginary Venue You Keep Within Your Head",
        'TRCK': "2"
    })


def make_m4a(path):
    silent_segment = AudioSegment.silent(duration=1000)
    file_path = Path(path) / "03 Sand.m4a"
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
        # @TODO: Replace with arbitrary folder generator
        show = phish_folder / Path("2024-01-01 Imaginary Venue You Keep Within Your Head")
        show.mkdir(parents=True)
        make_flac(show)
        make_mp3(show)
        make_m4a(show)
        show2 = phish_folder / Path("2024-01-02 Also Not a Venue")
        show2.mkdir(parents=True)
        # Return a dict
        yield {
            'tempdir': tempdir,
            'config_file': "phishtestpicks.json",
            'config_folder': str(Path(config_folder)),
            'phish_folder': str(Path(phish_folder)),
            'shows': [show, show2],
            'phish_db': "phish.db",
            'show_glob': "[0-9]*",
            'venue_regex': r'\d\d\d\d-\d\d-\d\d (.*?.*)'
        }
