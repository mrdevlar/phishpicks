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
from prompt_toolkit.key_binding import KeyBindings, KeyPress
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit import prompt


class DateTrackCompleter(Completer):
    def __init__(self, date_completer: list, tracks_from_date: Callable):
        date_completer.extend(['random', 'play', 'clear', 'shows', 'to_special', 'to_shows', 'exit'])
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
                track_names = [track.name for track in tracks]
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
        for word in track_names:
            word = word.lower()
            if word.startswith(word_before_cursor.lower()):
                yield Completion(text=word.title(), start_position=-len(word_before_cursor))


class PhishMenu(str):
    """ Special list for menu location """

    def __init__(self, *args):
        super(PhishMenu, self).__init__(*args)
        self._tree = []


class PhishREPL(BaseModel):
    pick: PhishPicks
    kb: Any = None
    keys: Any = None
    session: Any = None
    _menu: str = 'main'

    @property
    def menu(self):
        return self._menu

    @menu.setter
    def menu(self, value):
        self._menu = value

    def model_post_init(self, __context: Any):
        self.kb = KeyBindings()
        self.keys = []

        # @TODO: Add ctrl backspace
        # @TODO: Add ctrl arrows

        @self.kb.add('backspace')
        def up_menu(event):
            buffer = event.current_buffer
            if buffer.text == "" and buffer.cursor_position == 0:
                raise KeyboardInterrupt
            else:
                buffer.delete_before_cursor(count=1)

    @staticmethod
    def load(**kwargs) -> PhishREPL:
        pp = PhishPicks.load(**kwargs)
        return PhishREPL(pick=pp)

    @staticmethod
    def help_menu():
        speak_help = list()
        speak_help.append(" ")
        speak_help.append(" _____ COMMANDS _____ ")
        speak_help.append("  help: This List")
        speak_help.append(" shows: Select Shows")
        speak_help.append("tracks: Select Tracks")
        speak_help.append("random: Random Picks")
        speak_help.append("  play: Play Selection with Media Player")
        speak_help.append(" clear: Clear Picks")
        speak_help.append("  exit: Leave")
        speak_help.append(" ")
        speak_help.append(" _____ KEYBOARD _____ ")
        speak_help.append("Backspace: return to main menu / exit")
        speak_help.append("      Tab: cycle through autocomplete")
        speak_help.append("    Space: continues text")
        speak_help.append("    Enter: submits command")
        speak_help.append(" ")
        print("\n".join(speak_help))

    def shows_menu(self):
        date_completer = self.generic_commands_append(self.pick.db.all_show_dates)
        completer = WordCompleter(date_completer, WORD=True)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > shows > </style>')
        placeholder = HTML('<style color="#6A87A0">YYYY-MM-DD</style>')
        user_input = self.session.prompt(prompt_text, placeholder=placeholder, completer=completer,
                                         complete_while_typing=True, key_bindings=self.kb)
        if not user_input:
            print(self.pick.picks)
        elif user_input == 'random':
            self.pick.random_shows()
        elif user_input == 'play':
            self.pick.play()
        elif user_input == 'clear':
            self.pick.clear()
        elif user_input == 'tracks':
            self.pick.tracks()
        elif user_input == 'exit':
            raise KeyboardInterrupt
        else:
            selected_show, _ = self.extract_date(user_input)
            if not selected_show:
                print("Incomplete Date, Try Again")
            else:
                self.pick.pick_show(user_input.strip())

    def tracks_menu(self):
        date_completer = self.pick.db.all_show_dates()
        completer = DateTrackCompleter(date_completer, self.pick.db.tracks_from_date)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > tracks > </style>')
        placeholder = HTML('<style color="#6A87A0">YYYY-MM-DD TRACK_NAME</style>')
        user_input = self.session.prompt(prompt_text, placeholder=placeholder, completer=completer,
                                         complete_while_typing=True, key_bindings=self.kb)
        if not user_input:
            print(self.pick.picks)
        elif user_input == 'random':
            self.pick.random_tracks()
        elif user_input == 'play':
            self.pick.play()
        elif user_input == 'clear':
            self.pick.clear()
        elif user_input == 'shows':
            self.pick.shows()
        elif user_input == 'to_shows':
            self.pick.to_shows()
            self.menu = 'shows'
            self.shows_menu()
            raise KeyboardInterrupt
        elif user_input == 'to_special':
            self.pick.to_special()
            self.pick.db.backup_track_special()
        elif user_input == 'exit':
            raise KeyboardInterrupt
        else:
            show_date, track_name = self.extract_date(user_input)
            if not show_date or not track_name:
                print("Missing Values, Try Again")
            else:
                self.pick.pick_track(show_date, track_name, exact=True)

    def main_menu(self):
        menus = ['help', 'shows', 'tracks', 'random', 'play', 'clear', 'exit']
        completer = WordCompleter(menus)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > </style>')
        input = self.session.prompt(prompt_text,
                                    completer=completer,
                                    placeholder='',
                                    complete_while_typing=True,
                                    key_bindings=self.kb,
                                    )
        if input in menus:
            self.menu = input.strip()
        else:
            print(self.pick.picks)

    def generic_commands_run(self, user_input: str) -> str:
        if not user_input:
            print(self.pick.picks)
        elif user_input == 'random':
            self.pick.random_shows()
        elif user_input == 'play':
            self.pick.play()
        elif user_input == 'clear':
            self.pick.clear()
        else:
            return user_input

    @staticmethod
    def generic_commands_append(completer_func: Callable) -> list:
        completion_list = completer_func()
        commands = ['random', 'play', 'clear', ]
        completion_list.extend(commands)
        return completion_list

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

    def start(self):
        self.session = PromptSession()
        while True:
            try:
                if self._menu == 'main':
                    self.main_menu()
                elif self._menu == 'shows':
                    try:
                        self.shows_menu()
                    except KeyboardInterrupt:
                        self.menu = 'main'
                elif self._menu == 'tracks':
                    try:
                        self.tracks_menu()
                    except KeyboardInterrupt:
                        self.menu = 'main'
                elif self._menu == 'help':
                    self.help_menu()
                    self.menu = 'main'
                elif self._menu == 'random':
                    if self.pick.picks:
                        if self.pick.mode == 'shows':
                            self.pick.random_shows()
                            self.menu = 'shows'
                        elif self.pick.mode == 'tracks':
                            self.pick.random_tracks()
                            self.menu = 'tracks'
                        else:
                            print('Cannot')
                    else:
                        # No picks whatsoever
                        self.pick.random_shows()
                        self.menu = 'shows'
                elif self._menu == 'exit':
                    print("Goodbye")  # @TODO: Witty Exit
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                print("Goodbye")
                break


def main():
    c = PhishREPL.load()
    c.start()
