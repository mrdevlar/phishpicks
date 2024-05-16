from pathlib import Path
from datetime import date
from phishpicks import Configuration
from phishpicks import PhishData
from phishpicks.data import Show, Track


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
    db.update_played_show(selected_show)
    results = db.query_shows('shows.show_id == 1')
    assert len(results) == 1
    result = results[0]
    assert result.last_played == date.today()
    assert result.times_played == 1
    db.engine.dispose()


def test_reset_played_shows(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    db.reset_played_shows()
    results = db.query_shows('shows.show_id == 1')
    assert len(results) == 1
    result = results[0]
    assert result.last_played is None
    assert result.times_played == 0
    db.engine.dispose()


def test_update_special(settings):
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
                'disc_number': 1,
                'track_number': 1,
                'name': 'ghost',
                'filetype': '.flac',
                'length_sec': 2,
                'special': True}
    for k, v in expected.items():
        assert result_vars[k] == v
    db.engine.dispose()


def test_show_by_date(settings):
    config, db = load_or_create(settings)
    assert config.is_db()
    show = db.show_by_date('2024-03-07')
    assert isinstance(show, Show)
    show_vars = vars(show)
    expected = {'show_id': 3,
                'date': date(2024, 3, 7),
                'venue': "center of no man's land",
                'last_played': None,
                'times_played': 0,
                'folder_path': "2024-03-07 Center of No Man's Land"}
    for k, v in expected.items():
        assert show_vars[k] == v
    db.engine.dispose()
