from prompt_toolkit.document import Document
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.completion import CompleteEvent
from phishpicks import PhishREPL
from phishpicks.repl import DateTrackCompleter, TrackAfterDateCompleter


def repl_load(settings):
    return PhishREPL.load_diagnostic(
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
    doc_text = '2017-03'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = WordCompleter(date_completer, ignore_case=True, WORD=True)
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert len(completions) == 1
    assert '2017-03-07' in completions
    rp.pick.db.engine.dispose()


class StubSession:
    def __init__(self, response):
        self.response = response

    def prompt(self, *args, **kwargs):
        return self.response


def test_show_not_found(settings, capsys):
    rp = repl_load(settings)
    rp.session = StubSession('2099-01-01')
    rp.shows_menu()
    captured = capsys.readouterr()
    assert 'Show Not Found' in captured.out
    assert len(rp.pick.picks) == 0
    rp.pick.db.engine.dispose()


def test_show_found(settings, capsys):
    rp = repl_load(settings)
    rp.session = StubSession('2017-03-07')
    rp.shows_menu()
    captured = capsys.readouterr()
    assert 'Show Not Found' not in captured.out
    assert len(rp.pick.picks) == 1
    rp.pick.db.engine.dispose()


def test_tracks_no_shows_selected(settings, capsys):
    rp = repl_load(settings)
    rp.session = StubSession('tracks')
    rp.shows_menu()
    captured = capsys.readouterr()
    assert 'No Shows Selected' in captured.out
    assert len(rp.pick.picks) == 0
    rp.pick.db.engine.dispose()


def test_tracks_with_shows_selected(settings, capsys):
    rp = repl_load(settings)
    rp.pick.pick_show('2017-03-07')
    rp.session = StubSession('tracks')
    rp.shows_menu()
    captured = capsys.readouterr()
    assert 'No Shows Selected' not in captured.out
    assert 'Ghost' in captured.out
    rp.pick.db.engine.dispose()


def test_track_after_date_completer(settings):
    rp = repl_load(settings)
    tracks_from_date = rp.pick.db.tracks_from_date('2017-03-07')
    track_names = [track.name for track in tracks_from_date]
    doc_text = '2017-03-07 G'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = TrackAfterDateCompleter(track_names)
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert len(completions) == 1
    assert 'Ghost' in completions
    rp.pick.db.engine.dispose()
