from tempfile import TemporaryDirectory
from pathlib import Path
from phishpicks import Configuration
from phishpicks import PhishData


def test_configuration(settings):
    config = Configuration(
        config_file=settings['config_file'],
        config_folder=str(settings['config_folder']),
        phish_folder=str(settings['phish_folder']),
        show_glob=settings['show_glob'],
        venue_regex=settings['venue_regex']
    )
    config.create_configuration_folder()
    config.save_to_json()
    assert config.is_configuration_folder()
    assert config.is_phish_folder()
    assert config.total_phish_folders() == 2
    assert (Path(config.config_folder) / config.config_file).exists()


def test_db(settings):
    config = Configuration.from_json(config_file=settings['config_file'], config_folder=settings['config_folder'])
    pd = PhishData(config=config)
    pd.create()
    pd.populate()
    assert config.is_db()
    # Check Phish Folder Mapping
    all_shows = pd.all_shows()
    assert len(all_shows) == config.total_phish_folders()
    assert len(pd.tracks_from_show_ids(pd.all_shows())) == config.total_phish_songs()
    pd.engine.dispose()
