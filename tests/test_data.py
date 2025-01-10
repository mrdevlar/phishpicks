from pathlib import Path
from datetime import date, datetime

import pytest
from .conftest import make_mp3

from phishpicks import Configuration
from phishpicks import PhishData, Show, Track


def load_or_create(settings):
    if (Path(settings['config_folder']) / settings['phish_db']).exists():
        config = Configuration.from_json(config_file=settings['config_file'], config_folder=settings['config_folder'])
        db = PhishData(config=config)
    else:
        config = Configuration(
            config_file=settings['config_file'],
            config_folder=str(settings['config_folder']),
            backups_folder=str(settings['backups_folder']),
            phish_folder=str(settings['phish_folder']),
            show_glob=settings['show_glob'],
            venue_regex=settings['venue_regex'],
            media_player_path=settings['media_player_path']
        )
        db = config.configure()
    return config, db


def test_update_played(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    selected_show = db.show_from_id(1)
    db.update_played_show(selected_show.date.strftime('%Y-%m-%d'))
    results = db.query_shows('shows.show_id == 1')
    assert len(results) == 1
    result = results[0]
    last_played = result.last_played.replace(second=0, microsecond=0)
    assert last_played == datetime.now().replace(second=0, microsecond=0)
    assert result.times_played == 1
    db.engine.dispose()


def test_reset_played_shows(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    selected_show = db.show_from_id(1)
    db.update_played_show(selected_show.date.strftime('%Y-%m-%d'))
    db.reset_played_shows([selected_show])
    results = db.query_shows('shows.show_id == 1')
    assert len(results) == 1
    result = results[0]
    assert result.last_played is None
    assert result.times_played == 0
    db.engine.dispose()


def test_all_show_dates(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    show_dates = db.all_show_dates()
    folder_dates = sorted([fake['album'][:10] for fake in settings['fake']])
    for x, y in zip(show_dates, folder_dates):
        assert x == y
    db.engine.dispose()


def test_all_track_names(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    track_names = db.all_track_names()
    flat_list = [item.lower() for sublist in settings['fake'] for item in sublist['tracks']]
    assert set(track_names) == set(flat_list)
    db.engine.dispose()


def test_update_special_tracks(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    selected_track = db.track_from_id(1)
    db.update_special_track(selected_track)
    results = db.all_special_tracks()
    assert len(results) == 1
    result = results[0]
    result_vars = vars(result)
    expected = {'track_id': 1,
                'show_id': 1,
                'disc_number': 3,
                'track_number': 1,
                'name': 'ghost',
                'filetype': '.m4a',
                'length_sec': 1,
                'special': True}
    for k, v in expected.items():
        assert result_vars[k] == v
    db.engine.dispose()


def test_update_special_shows(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    selected_show = db.show_from_id(3)
    db.update_special_show(selected_show)
    results = db.all_special_shows()
    assert len(results) == 1
    result = results[0]
    result_vars = vars(result)
    expected = {'show_id': 3,
                'date': date(2024, 1, 2),
                'venue': 'spaceship from scent of a mule',
                'last_played': None,
                'times_played': 0,
                'folder_path': '2024-01-02 Spaceship from Scent of a Mule',
                'special': True}
    for k, v in expected.items():
        assert result_vars[k] == v
    db.engine.dispose()


def test_show_by_date(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    with pytest.raises(ValueError):
        db.show_by_date('2024-03-07')
    show = db.show_by_date('2017-03-07')
    assert isinstance(show, Show)
    show_vars = vars(show)
    expected = {'show_id': 1,
                'date': date(2017, 3, 7),
                'venue': "center of no man's land",
                'last_played': None,
                'times_played': 0,
                'folder_path': "2017-03-07 Center of No Man's Land"}
    for k, v in expected.items():
        assert show_vars[k] == v
    db.engine.dispose()


def test_tracks_by_name(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    tracks = db.tracks_by_name('Ghost')
    assert len(tracks) == 2
    for t in tracks:
        assert 'ghost' in t.name
        assert isinstance(t, Track)
    db.engine.dispose()


def test_track_by_date_name(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    show, track = db.track_by_date_name('2017-03-07', 'Didn')[0]
    expected_show = {'show_id': 1,
                     'date': date(2017, 3, 7),
                     'venue': "center of no man's land",
                     'last_played': None,
                     'times_played': 0,
                     'folder_path': "2017-03-07 Center of No Man's Land"}
    expected_track = {'track_id': 2,
                      'show_id': 1,
                      'disc_number': 3,
                      'track_number': 2,
                      'name': "i didn't know",
                      'filetype': '.m4a',
                      'length_sec': 1,
                      'special': False, }
    show_vars = vars(show)
    track_vars = vars(track)
    for k, v in expected_show.items():
        assert show_vars[k] == v
    for k, v in expected_track.items():
        assert track_vars[k] == v
    db.engine.dispose()


def test_show_update(settings):
    config, db = load_or_create(settings)
    assert config.is_db()

    fake = {"album": "2025-10-15 Being, Consciousness, Bliss",
            "tracks": ['Ghost', 'Mercury', 'Ruby Waves', "Simple", 'Sand'],
            "extension": "mp3"}

    show = settings['phish_folder'] / Path(fake['album'])
    show.mkdir(parents=True, exist_ok=True)
    for idx, track in enumerate(fake['tracks']):
        idx = idx + 1
        make_mp3({
            'path': show,
            'name': track,
            'album': fake['album'],
            'track_number': str(idx),
            'disc_number': "2/3",
            'artist': "Phish"
        })
    db.update()

    show_dates = db.all_show_dates()
    assert '2025-10-15' in show_dates

    new_show = db.show_by_date('2025-10-15')
    assert dict(new_show) == {'show_id': 7, 'date': date(2025, 10, 15),
                              'venue': 'being, consciousness, bliss',
                              'last_played': None,
                              'times_played': 0,
                              'folder_path': '2025-10-15 Being, Consciousness, Bliss',
                              'special': False}

    new_tracks = db.tracks_from_date('2025-10-15')
    assert len(new_tracks) == 5
    
    db.engine.dispose()

def test_restore_all(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    selected_show = db.show_from_id(1)
    selected_track = db.track_from_id(1)
    selected_track2 = db.track_from_id(2)
    db.update_played_show(selected_show.date.strftime('%Y-%m-%d'))
    db.update_special_show(selected_show)
    db.update_special_track(selected_track)
    db.update_special_track(selected_track2)
    db.backup_all()
    db.restore_all()
    db.engine.dispose()


def test_reset_db(settings):
    config, db = load_or_create(settings)
    assert config.is_db()

    db.reset_db()
    assert config.is_db()
    db.engine.dispose()


