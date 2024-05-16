from pathlib import Path
from phishpicks import Configuration


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
    assert config.total_phish_folders() == 5
    assert config.total_phish_songs() == config.total_phish_songs()
    assert config.total_phish_songs() == 25
    assert (Path(config.config_folder) / config.config_file).exists()
    db.engine.dispose()


def test_delete_config(settings):
    config = Configuration.from_json(config_file=settings['config_file'], config_folder=settings['config_folder'])
    config.delete_configuration_folder()
    assert not Path(settings['config_folder']).exists()


def test_configure(settings):
    config = Configuration(
        config_file=settings['config_file'],
        config_folder=str(settings['config_folder']),
        backups_folder=str(settings['backups_folder']),
        phish_folder=str(settings['phish_folder']),
        show_glob=settings['show_glob'],
        venue_regex=settings['venue_regex'],
        media_player_path=settings['media_player_path']
    )
    config.configure()
    assert Path(settings['phish_folder']).exists()
    assert Path(settings['media_player_path']).exists()
    assert Path(settings['config_folder']).exists()
    assert (Path(settings['config_folder']) / settings['config_file']).exists()
    assert Path(settings['backups_folder']).exists()
    assert (Path(settings['config_folder']) / settings['phish_db']).exists()
