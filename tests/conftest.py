import shutil

import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3


def make_flac(path):
    audio = FLAC()

    # Add tags
    audio["title"] = "Ghost"
    audio["artist"] = "Phish"
    audio["album"] = "2024-01-01 Imaginary Venue You Keep Within Your Head"

    # Save the new FLAC file
    audio.save(Path(path) / "test.flac")


@pytest.fixture(scope="session", autouse=True)
def settings():
    with TemporaryDirectory() as tempdir:
        config_folder = Path(tempdir) / Path(".testpicks")
        phish_folder = Path(tempdir) / Path("PhishTest")
        phish_folder.mkdir(parents=True)
        # @TODO: Replace with arbitrary folder generator
        show = phish_folder / Path("2024-01-01 Imaginary Venue You Keep Within Your Head")
        show.mkdir(parents=True)
        # make_flac(show)
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
