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


def generate_fake_phish_folder(tempdir):
    fake_shows = [
        {"album": "2024-01-01 Imaginary Venue You Keep Within Your Head",
         "tracks": ['Ghost', 'Bouncing Around The Room', 'Harpua', 'Sand', 'We Are Come To Outlive Our Brains'],
         "extension": "flac"},
        {"album": "2024-01-02 Spaceship from Scent of a Mule",
         "tracks": ['Gotta Jibboo', 'Simple', 'The Old Home Place', 'Twenty Years Later', 'Water In The Sky'],
         "extension": "mp3"},
        {"album": "2024-03-07 Center of No Man's Land",
         "tracks": ['Dog Faced Boy', "I Didn'T Know", 'Mock Song', 'Suzy Greenberg', 'Undermind'],
         "extension": "m4a"},
        {"album": "2024-04-20 Drew Carey Presents The Sphere",
         "tracks": ['Backwards Down The Number Line', 'Driver', 'Horn', 'Ruby Waves', 'Split Open And Melt'],
         "extension": "flac"},
        {"album": "2024-05-15 In the Tail of Hailey's Comet",
         "tracks": ['Heavy Things', 'If I Could', 'Tube', "Wolfman'S Brother", 'You Enjoy Myself'],
         "extension": "mp3"},
    ]
    for fake in fake_shows:
        yield fake


@pytest.fixture(scope="session", autouse=True)
def settings():
    with TemporaryDirectory() as tempdir:
        config_folder = Path(tempdir) / Path(".testpicks")
        backup_folder = Path(tempdir) / Path(".testpicks_backups")
        phish_folder = Path(tempdir) / Path("PhishTest")
        phish_folder.mkdir(parents=True)
        media_player_path = Path(tempdir) / Path('winamp.exe')
        media_player_path.touch()
        # @TODO: Replace with arbitrary folder generator
        for fake in generate_fake_phish_folder(tempdir):
            show = phish_folder / Path(fake['album'])
            show.mkdir(parents=True, exist_ok=True)
            for idx, track in enumerate(fake['tracks']):
                idx = idx + 1
                if fake['extension'] == 'flac':
                    make_flac(track_dict(show, track, fake['album'], str(idx), "1/3", "Phish"))
                elif fake['extension'] == 'mp3':
                    make_mp3(track_dict(show, track, fake['album'], str(idx), "2/3", "Phish"))
                elif fake['extension'] == 'm4a':
                    make_m4a(track_dict(show, track, fake['album'], str(idx), "3/3", "Phish"))
                else:
                    raise ValueError("No Extension Available")
        yield {
            'tempdir': tempdir,
            'config_file': "phishtestpicks.json",
            'config_folder': str(Path(config_folder)),
            'backup_folder': str(Path(backup_folder)),
            'phish_folder': str(Path(phish_folder)),
            'phish_db': "phish.db",
            'show_glob': "[0-9]*",
            'venue_regex': r'\d\d\d\d-\d\d-\d\d (.*?.*)',
            'media_player_path': str(Path(media_player_path)),
            'fake': generate_fake_phish_folder(tempdir),
        }
