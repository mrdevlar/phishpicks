import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from pydub import AudioSegment
from mutagen.easymp4 import EasyMP4Tags


def track_dict(path, name, album, track_number, disc_number, artist):
    return {
        'path': path,
        'name': name,
        'album': album,
        'track_number': track_number,
        'disc_number': disc_number,
        'artist': artist
    }


def make_flac(track_dict: dict):
    silent_segment = AudioSegment.silent(duration=2000)
    file_path = Path(track_dict['path']) / f"{track_dict['track_number']} {track_dict['name']}.flac"
    silent_segment.export(file_path, format="flac", tags={
        "title": track_dict['name'],
        "artist": track_dict['artist'],
        "album": track_dict['album'],
        "tracknumber": track_dict['track_number'],
        "discnumber": track_dict['disc_number'],
    })


def make_mp3(track_dict: dict):
    silent_segment = AudioSegment.silent(duration=1000)
    file_path = Path(track_dict['path']) / f"{track_dict['track_number']} {track_dict['name']}.mp3"
    silent_segment.export(file_path, format="mp3", tags={
        'TIT2': track_dict['name'],
        'TPE1': track_dict['artist'],
        'TALB': track_dict['album'],
        'TRCK': track_dict['track_number'],
        'TPOS': track_dict['disc_number']
    })


def make_m4a(track_dict: dict):
    silent_segment = AudioSegment.silent(duration=1000)
    file_path = Path(track_dict['path']) / f"{track_dict['track_number']} {track_dict['name']}.m4a"
    # AudioSegment tags don't work for mp4
    silent_segment.export(file_path, format="mp4")
    new_tags = {
        "artist": track_dict['artist'],
        "albumartist": track_dict['artist'],
        "discnumber": track_dict['disc_number'],
        "tracknumber": track_dict['track_number'],
        "title": track_dict['name'],
        "album": track_dict['album'],
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
        album2 = "2024-01-02 Spaceship from Scent of a Mule"
        album3 = "2024-03-07 Center of No Man's Land"
        album4 = "2024-04-20 Drew Carey Presents The Sphere"
        album5 = "2024-05-15 In the Tail of Hailey's Comet"
        show = phish_folder / Path(album1)
        show.mkdir(parents=True)
        make_flac(track_dict(show, "Ghost", album1, "1", "0", "Phish"))
        make_mp3(track_dict(show, "Everything's Right", album1, "2", "0", "Phish"))
        show2 = phish_folder / Path(album2)
        show2.mkdir(parents=True)
        make_m4a(track_dict(show2, "Sand", album2, "3", "1", "Phish"))
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
