from phishpicks.repl import *
from prompt_toolkit.document import Document
from prompt_toolkit.completion import (
    CompleteEvent
)


def test_main_menu():
    doc_text = 't'
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completer = WordCompleter(['main', 'help', 'shows', 'tracks', 'exit'])
    completions = [c.text for c in completer.get_completions(doc, event)]
    assert 'tracks' in completions
