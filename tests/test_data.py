from datetime import date
from pathlib import Path
from phishpicks import Configuration
from phishpicks import PhishData


def test_configuration(settings):
    config = Configuration(
        config_file=settings['config_file'],
        config_folder=str(settings['config_folder']),
        phish_folder=str(settings['phish_folder']),
        show_glob=settings['show_glob'],
        venue_regex=settings['venue_regex'],
        media_player_path=settings['media_player_path']
    )
    config.create_configuration_folder()
    config.save_to_json()
    assert config.is_configuration_folder()
    assert config.is_phish_folder()
    assert config.total_phish_folders() == 2
    assert (Path(config.config_folder) / config.config_file).exists()


def test_db_build(settings):
    config = Configuration.from_json(config_file=settings['config_file'], config_folder=settings['config_folder'])
    pd = PhishData(config=config)
    pd.create()
    pd.populate()
    assert config.is_db()
    # Check Phish Folder Mapping
    all_shows = pd.all_shows()
    assert len(all_shows) == config.total_phish_folders()
    assert len(pd.tracks_from_shows(pd.all_shows())) == config.total_phish_songs()
    pd.engine.dispose()


def test_db_update_played(settings):
    config = Configuration.from_json(config_file=settings['config_file'], config_folder=settings['config_folder'])
    pd = PhishData(config=config)
    assert config.is_db()
    selected_show = pd.show_from_id(1)
    pd.update_played_show(selected_show)
    results = pd.query_shows('shows.show_id == 1')
    assert len(results) == 1
    result = results[0]
    assert result.last_played == date.today()
    assert result.times_played == 1
    pd.engine.dispose()


def test_db_update_special(settings):
    config = Configuration.from_json(config_file=settings['config_file'], config_folder=settings['config_folder'])
    pd = PhishData(config=config)
    assert config.is_db()
    selected_track = pd.track_from_id(1)
    pd.update_special_track(selected_track)
    results = pd.all_special_tracks()
    assert len(results) == 1
    result = results[0]
    result_vars = vars(result)
    expected = {'track_id': 1,
                'show_id': 1,
                'disc_number': 0,
                'track_number': 1,
                'name': 'ghost',
                'filetype': '.flac',
                'length_sec': 2,
                'special': True}
    assert all([(result_vars[k] == v) for (k, v) in expected.items()])
    pd.engine.dispose()
