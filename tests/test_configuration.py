from pathlib import Path
from phishpicks import Configuration


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
