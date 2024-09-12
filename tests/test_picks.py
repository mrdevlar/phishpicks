from phishpicks import PhishPicks
from phishpicks import Configuration
from phishpicks import PhishData
from phishpicks.picks import PhishSelection
from phishpicks import Show, Track


def pp_load(settings):
    return PhishPicks.load(
        config_file=settings['config_file'],
        config_folder=str(settings['config_folder']),
        backups_folder=str(settings['backups_folder']),
        phish_folder=str(settings['phish_folder']),
        show_glob=settings['show_glob'],
        venue_regex=settings['venue_regex'],
        media_player_path=settings['media_player_path']
    )


def test_picks_load(settings):
    pp = pp_load(settings)
    assert isinstance(pp, PhishPicks)
    assert isinstance(pp.db, PhishData)
    assert isinstance(pp.config, Configuration)
    assert isinstance(pp.picks, PhishSelection)
    assert pp.config.is_configured()
    pp.db.engine.dispose()


def test_random_shows(settings):
    pp = pp_load(settings)
    pp.random_shows(2)
    assert pp._mode == 'shows'
    assert len(pp.picks) == 2
    for show in pp.picks:
        assert isinstance(show, Show)
    pp.clear()
    assert len(pp.picks) == 0
    pp.db.engine.dispose()


def test_random_tracks(settings):
    pp = pp_load(settings)
    pp.random_tracks(3)
    assert pp._mode == 'tracks'
    assert len(pp.picks) == 3
    for track in pp.picks:
        assert isinstance(track, Track)
    pp.clear()
    assert len(pp.picks) == 0
    pp.db.engine.dispose()


def test_to_special(settings):
    pp = pp_load(settings)
    pp.random_tracks(1)
    pp.to_special()
    assert len(pp.picks) == 1
    for track in pp.picks:
        assert track.special is True
    pp.db.engine.dispose()
