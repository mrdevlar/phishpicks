import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from pydub import AudioSegment
from mutagen.easymp4 import EasyMP4Tags
from phishpicks import Configuration

def pytest_configure():
    print("pytest_configure called")

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
        {"album": "2017-03-07 Center of No Man's Land",
         "tracks": ['Ghost', "I Didn'T Know", 'Mock Song', 'Suzy Greenberg', 'Undermind'],
         "extension": "m4a"},
        {"album": "2024-04-20 Drew Carey Presents The Sphere",
         "tracks": ['Backwards Down The Number Line', 'Driver', 'Horn', 'Ruby Waves', 'Split Open And Melt'],
         "extension": "flac"},
        {"album": "2025-05-15 In the Tail of Hailey's Comet",
         "tracks": ['Heavy Things', 'If I Could', 'Tube', "Wolfman'S Brother", 'You Enjoy Myself'],
         "extension": "mp3"},
        {"album": "2025-08-22 In A Really Long Tube",
         "tracks": ['Tube', 'Harry Hood', 'Tube', "Plasma", 'Light'],
         "extension": "flac"},
    ]
    return fake_shows

def test_settings_configuration(settings):
    """
    Tests conftest settings() and Configuration class
    Tests alternate between settings and Configs
    Args:
        settings: conftest settings()
    """
    config = Configuration(
        config_file=settings['config_file'],
        config_folder=str(settings['config_folder']),
        backups_folder=str(settings['backups_folder']),
        phish_folder=str(settings['phish_folder']),
        show_glob=settings['show_glob'],
        venue_regex=settings['venue_regex'],
        media_player_path=settings['media_player_path']
    )
    assert Path(settings['phish_folder']).exists()
    assert config.is_phish_folder()
    assert Path(settings['media_player_path']).exists()
    assert config.is_media_player()
    config.create_configuration_folder()
    assert Path(settings['config_folder']).exists()
    assert config.is_configuration_folder()
    config.save_to_json()
    assert (Path(settings['config_folder']) / settings['config_file']).exists()
    assert config.is_configuration_file()
    config.create_backups_folder()
    assert Path(settings['backups_folder']).exists()
    assert config.is_backups_folder()
    db = config.create_configure_db()
    assert config.is_db()
    all_shows = db.all_shows()
    assert len(all_shows) == config.total_phish_folders()
    assert config.total_phish_folders() == 6
    assert config.total_phish_songs() == config.total_phish_songs()
    assert config.total_phish_songs() == 30
    assert (Path(config.config_folder) / config.config_file).exists()
    db.engine.dispose()

@pytest.fixture(scope="session", autouse=True)
def settings():
    with TemporaryDirectory() as tempdir:
        config_folder = Path(tempdir) / Path(".testpicks")
        # config_folder.touch()
        backups_folder = Path(tempdir) / Path(".testpicks_backups")
        # backups_folder.touch()
        phish_folder = Path(tempdir) / Path("PhishTest")
        phish_folder.mkdir(parents=True)
        media_player_path = Path(tempdir) / Path('foobar')
        media_player_path.touch()
        config_file = "phishtestpicks.json"

        config_folder = str(Path(config_folder))
        backups_folder = str(Path(backups_folder))
        phish_folder = str(Path(phish_folder))
        phish_db = "phish.db"
        show_glob = "[0-9]*"
        venue_regex = r'\d\d\d\d-\d\d-\d\d (.*?.*)'
        media_player_path = str(Path(media_player_path))
        afake = generate_fake_phish_folder(tempdir)

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

        config = Configuration(
            config_file=config_file,
            config_folder=config_folder,
            backups_folder=backups_folder,
            phish_folder=phish_folder,
            show_glob=show_glob,
            venue_regex=venue_regex,
            media_player_path=media_player_path,
        )
        assert Path(phish_folder).exists()
        assert config.is_phish_folder()
        assert Path(media_player_path).exists()
        assert config.is_media_player()
        config.create_configuration_folder()
        assert Path(config_folder).exists()
        assert config.is_configuration_folder()
        config.save_to_json()
        assert (Path(config_folder) / config_file).exists()
        assert config.is_configuration_file()
        config.create_backups_folder()
        assert Path(backups_folder).exists()
        assert config.is_backups_folder()
        db = config.create_configure_db()
        assert config.is_db()
        all_shows = db.all_shows()
        assert len(all_shows) == config.total_phish_folders()
        assert config.total_phish_folders() == 6
        assert config.total_phish_songs() == config.total_phish_songs()
        assert config.total_phish_songs() == 30
        assert (Path(config.config_folder) / config.config_file).exists()
        db.engine.dispose()
        yield {
            'tempdir': tempdir,
            'config_file': config_file,
            'config_folder': config_folder,
            'backups_folder': backups_folder,
            'phish_folder': phish_folder,
            'phish_db': phish_db,
            'show_glob': show_glob,
            'venue_regex': venue_regex,
            'media_player_path': media_player_path,
            'fake': afake,
        }
