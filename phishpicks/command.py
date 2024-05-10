from __future__ import annotations
import re
from datetime import datetime
from typing import Callable, Iterable, Any
from phishpicks import PhishPicks
from pydantic import BaseModel
from prompt_toolkit.completion import WordCompleter, Completer, CompleteEvent, Completion
from prompt_toolkit.completion import Completer
from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding import KeyBindings


class PhishCommand(BaseModel):
    pick: PhishPicks
    kb: Any = None
    keys: Any = None
    session: Any = None
    _mode: str = 'main'
    available_modes: list = ['main', 'help', 'show', 'track', 'exit']

    # @TODO: Add upward history

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value
        # if value in self.available_modes:
        #     if value != self._mode:
        #         self.clear()
        #     self._mode = value
        # else:
        #     raise TypeError(f"mode must be one of {self.available_modes}")

    def model_post_init(self, __context: Any):
        self.kb = KeyBindings()
        self.keys = []
        self.session = PromptSession()

        @self.kb.add(Keys.ControlD)
        def _(event):
            # print(event.is_repeat)
            # print(dir(event.app))
            event.app.exit()
            # event.app.current_buffer.exit_selection()
            # event.cli.set_return_value(Keys.ControlD)

    @staticmethod
    def load(**kwargs) -> PhishCommand:
        pp = PhishPicks.load(**kwargs)
        return PhishCommand(pick=pp)

    def clear(self):
        self.pick.clear()

    def main_menu(self):
        # print(self.pick.picks)
        completer = WordCompleter(self.available_modes)
        option = self.session.prompt('phishpicks > ', completer=completer, complete_while_typing=True,
                                     key_bindings=self.kb)
        if option in self.available_modes:
            self.mode = option.strip()
        else:
            print(self.pick.picks)

    def track_menu(self):
        self.mode = 'track'
        date_completer = self.pick.db.all_show_dates()
        completer = DateTrackCompleter(date_completer, self.pick.db.tracks_from_date)
        track = self.session.prompt('phishpicks > tracks > ', placeholder='YYYY-MM-DD TRACK_NAME', completer=completer,
                                    complete_while_typing=True, key_bindings=self.kb)
        if not track:
            print(self.pick.picks.__repr__())
            self.session.app.exit()
            print(dir(self.session.app))
        show_date, track_name = self.extract_date(track)
        if not show_date or not track_name:
            print("Missing Values, Try Again")  # Format me
            # insert the text back
        else:
            self.pick.pick_track(show_date, track_name)

    def main(self):
        while True:
            if self._mode == 'main':
                self.main_menu()
            elif self._mode == 'track':
                self.track_menu()
            else:
                break

    @staticmethod
    def extract_date(select_statement):
        """ Extracts the date from the selection statement """
        # Regular expression to match a date in format YYYY-MM-DD
        date_regex = r'\d{4}-\d{2}-\d{2}'
        date_match = re.search(date_regex, select_statement)

        # If a date is found, return it and everything else
        if date_match:
            date_str = date_match.group(0)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date = date_obj.strftime('%Y-%m-%d')

            rest = select_statement.replace(date_str, '').strip()
            return date, rest
        else:
            return None, select_statement


class DateTrackCompleter(Completer):
    def __init__(self, date_completer: list, tracks_from_date: Callable):
        self.date_completer = WordCompleter(date_completer, ignore_case=True, WORD=True)
        self.tracks_from_date = tracks_from_date

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        text = document.text
        date_regex = r'(^\d{4}-\d{2}-\d{2})'
        if re.match(date_regex, text):
            date = ''
            name = ''
            text_split = re.split(date_regex, text)
            if len(text_split) == 3:
                date = text_split[1].strip()
                name = text_split[2]
            # Initial Date Return
            tracks = self.tracks_from_date(date)
            if name:
                # print(date, name)
                track_names = [track.name for track in tracks]
                # print(track_names)
                track_names = TrackAfterDateCompleter(track_names)
            else:
                track_names = WordCompleter([])
            completer = track_names
        else:
            completer = self.date_completer

        return completer.get_completions(document, complete_event)


class TrackAfterDateCompleter(Completer):
    def __init__(self, track_names):
        self.track_names = track_names

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        track_names = self.track_names
        if callable(track_names):
            track_names = track_names()

        date_regex = r'(^\d{4}-\d{2}-\d{2})'
        word_before_cursor = document.text_before_cursor
        word_before_cursor = re.sub(date_regex, '', word_before_cursor).strip()
        # print(word_before_cursor, end='\n')
        # print(track_names)
        for word in track_names:
            word = word.lower()
            # print(word)
            # print(word_before_cursor)
            if word.startswith(word_before_cursor.lower()):
                # print(word)
                # print(track_names)
                yield Completion(text=word.title(), start_position=-len(word_before_cursor))


pc = PhishCommand.load()
pc.main()
