from prompt_toolkit.document import Document
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.completion import CompleteEvent
from phishpicks import PhishREPL
from phishpicks.repl import DateTrackCompleter, TrackAfterDateCompleter


def repl_load(settings):
    return PhishREPL.load(
        config_file=settings['config_file'],
        config_folder=str(settings['config_folder']),
        backups_folder=str(settings['backups_folder']),
        phish_folder=str(settings['phish_folder']),
        show_glob=settings['show_glob'],
        venue_regex=settings['venue_regex'],
        media_player_path=settings['media_player_path']
    )


def test_date_completer(settings):
    """ Test Date Completer, currently Generic WordCompleter """
    rp = repl_load(settings)
    date_completer = rp.pick.db.all_show_dates()
    doc_text = '2024-03'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = WordCompleter(date_completer, ignore_case=True, WORD=True)
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert len(completions) == 1
    assert '2024-03-07' in completions
    rp.pick.db.engine.dispose()


def test_track_after_date_completer(settings):
    rp = repl_load(settings)
    tracks_from_date = rp.pick.db.tracks_from_date('2024-03-07')
    track_names = [track.name for track in tracks_from_date]
    doc_text = '2024-03-07 G'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = TrackAfterDateCompleter(track_names)
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert len(completions) == 1
    assert 'Ghost' in completions
    rp.pick.db.engine.dispose()


def test_tracks_after_date_completer(settings):
    rp = repl_load(settings)
    tracks_from_date = rp.pick.db.tracks_from_date('2024-03-07')
    track_names = [track.name for track in tracks_from_date]
    doc_text = '2024-03-07'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = TrackAfterDateCompleter(track_names)
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert len(completions) == 5
    expected = ['Ghost', "I Didn'T Know", 'Mock Song', 'Suzy Greenberg', 'Undermind']
    for x, y in zip(completions, expected):
        assert x == y
    rp.pick.db.engine.dispose()


def test_date_track_completer_date(settings):
    rp = repl_load(settings)
    date_completer = rp.pick.db.all_show_dates()
    tracks_from_date = rp.pick.db.tracks_from_date
    doc_text = '2024-03'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = DateTrackCompleter(date_completer, tracks_from_date)
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert len(completions) == 1
    assert '2024-03-07' in completions
    rp.pick.db.engine.dispose()


def test_date_track_completer_track(settings):
    rp = repl_load(settings)
    date_completer = rp.pick.db.all_show_dates()
    tracks_from_date = rp.pick.db.tracks_from_date
    doc_text = '2024-03-07 G'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = DateTrackCompleter(date_completer, tracks_from_date)
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert len(completions) == 1
    assert 'Ghost' in completions
    rp.pick.db.engine.dispose()
