from __future__ import annotations
import re
from datetime import datetime
from typing import Callable, Iterable, Any
from phishpicks import Configuration, PhishData, PhishPicks
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
import pdb
import inspect


# @TODO: Add ctrl backspace
# @TODO: Add ctrl arrows
class PhishREPL(BaseModel):
    pick: PhishPicks
    kb: Any = None
    keys: Any = None
    session: Any = None
    _menu: str = 'main'
    diagnostic_mode: bool = False

    @property
    def menu(self):
        return self._menu

    @menu.setter
    def menu(self, value):
        self._menu = value

    def model_post_init(self, __context: Any):
        self.kb = KeyBindings()
        self.keys = []
        if not self.diagnostic_mode:
            # This flag is set because the prompt session prevents
            # CMD from executing properly on Windows Machines
            # This allows for testing
            self.session = PromptSession()

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
    def load_diagnostic(**kwargs) -> PhishREPL:
        """
        Diagnostic Loader for testing
        """
        conf = Configuration()
        pp = PhishPicks.load(**kwargs)
        return PhishREPL(pick=pp, diagnostic_mode=True)

    def main_menu(self):
        menus = ['help', 'configure', 'data', 'dap', 'shows', 'tracks', 'random', 'play', 'clear', 'exit']
        completer = WordCompleter(menus)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > </style>')
        main_selection = self.session.prompt(prompt_text,
                                             completer=completer,
                                             placeholder='',
                                             complete_while_typing=True,
                                             key_bindings=self.kb,
                                             )
        if main_selection and main_selection in menus:
            return main_selection
        else:
            print("Please make a selection or type `help` for commands")
            return 'main'

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
        elif user_input == 'help':
            self.help_menu()
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
        elif user_input == 'help':
            self.help_menu()
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

    def data_menu(self):
        all_data_methods = [func for func in dir(PhishData)
                            if callable(getattr(PhishData, func)) and not func.startswith('_')]
        #@TODO: Replace with function completer
        data_completer = WordCompleter(all_data_methods, ignore_case=True, WORD=True)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > data > </style>')
        placeholder = HTML('<style color="#6A87A0">PhishData Method</style>')
        user_input = self.session.prompt(prompt_text, placeholder=placeholder, completer=data_completer,
                                         complete_while_typing=True, key_bindings=self.kb)
        user_input_list = user_input.rstrip().split(" ")
        method_name = user_input_list.pop(0)
        if method_name in all_data_methods:
            method = getattr(self.pick.db, method_name)
            if user_input_list:
                print(method(*user_input_list))
            else:
                print(method())
        else:
            print('data method not found')

    def dap_menu(self):
        raise NotImplementedError

    def help_menu(self):
        speak_help = list()
        speak_help.append(" ")
        speak_help.append(" _____ COMMANDS _____ ")
        speak_help.append("     help: This List")
        speak_help.append("    shows: Select Shows")
        speak_help.append("   tracks: Select Tracks")
        speak_help.append("   random: Random Picks")
        speak_help.append("configure: Launch Configuration Wizard")
        speak_help.append("     data: Launch Database Operations")
        speak_help.append("      dap: Digital Audio Player Functions")
        speak_help.append("     play: Play Selection with Media Player")
        speak_help.append("    clear: Clear Picks")
        speak_help.append("     exit: Leave")
        speak_help.append(" ")
        speak_help.append(" _____ KEYBOARD _____ ")
        speak_help.append("Backspace: return to main menu / exit")
        speak_help.append("      Tab: cycle through autocomplete")
        speak_help.append("    Space: continues text")
        speak_help.append("    Enter: submits command")
        speak_help.append(" ")
        print("\n".join(speak_help))

    @staticmethod
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
        while True:
            try:
                if self._menu == 'main':
                    self.pick.db.update(verbose=False)
                    self._menu = self.main_menu()
                elif self._menu == 'configure':
                    config = configuration_prompts()
                    if config:
                        config.save_to_json()
                    self.menu = 'main'
                elif self._menu == 'data':
                    try:
                        self.data_menu()
                    except KeyboardInterrupt:
                        self.menu = 'main'
                elif self._menu == 'dap':
                    try:
                        self.dap_menu()
                    except KeyboardInterrupt:
                        self.menu = 'main'
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
                        # No picks whatsoever
                        self.pick.random_shows()
                        self.menu = 'shows'
                elif self._menu == 'exit':
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                print("Surrender to the Flow")
                self.pick.db.backup_all()
                break


def configuration_flow() -> Configuration:
    try:
        conf = Configuration.from_json()
    except FileNotFoundError:
        print("\nConfiguration Not Found")
        conf = configuration_prompts()
        if conf:
            conf.configure()
    return conf


def configuration_prompts() -> Configuration:
    session = PromptSession()
    kb = KeyBindings()
    # print("Current Configuration")
    # for key, value in self.config.dict().items():
    #     print(f"{key!s:>25}: {value}")
    # print("\n")

    # What is the path to your phish folder?
    # [0] "Z://Music//Phish"
    # OR Manually enter a phish_folder
    print("Starting Configuration Wizard\n")
    print(f"Phish Folder:\n[0]: {Configuration.model_fields['phish_folder'].default}\n")
    print("OR Manually enter a phish_folder")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > phish_folder > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['', '0']:
        phish_folder = Configuration.model_fields['phish_folder'].default
    else:
        phish_folder = user_input
    print(f"Phish Folder set to {phish_folder}")
    print("\n")

    # What is the format of your show folders?
    # Dates MUST be in posix format so YYYY-MM-DD, e.g. 2025-01-01 etc.
    # [0] Phish [0-9]* will match "Phish 2024-01-01 Some venue" style folders
    # [1] [0-9]* will match "2024-01-01 Some venue" style folders
    # OR Manually enter a show_glob and a venue_regex
    # Set the show_glob AND the venue_regex
    # Check and print the number of folders after configuration
    print(f"Show Folder Format")
    print(f"[0] Phish [0-9]* will match 'Phish 2024-01-01 Some venue' style folders")
    print(f"[1] [0-9]* will match '2024-01-01 Some venue' style folders")
    print("OR Manually enter a show_glob")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > show_glob > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['', '0']:
        show_glob = Configuration.model_fields['show_glob'].default
        venue_regex = Configuration.model_fields['venue_regex'].default
    elif user_input in ['1']:
        show_glob = "[0-9]*"
        venue_regex = r'\d\d\d\d-\d\d-\d\d (.*?.*)'
    else:
        show_glob = user_input
        venue_regex = HTML('<style color="#FFDC00">phishpicks > configuration > venue_regex > </style>')
    print(f"Show Glob Format set to: {show_glob}")
    print("\n")

    # What is your desired configuration folder?
    # [0] "~/.phishpicks"
    # OR Manually enter config_folder
    print("Configuration Folder")
    print(f"[0] {Configuration.model_fields['config_folder'].default}")
    print("OR Manually enter a config_folder")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > config_folder > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['', '0']:
        config_folder = Configuration.model_fields['config_folder'].default
    else:
        config_folder = user_input
    print(f"Configuration Folder set to {config_folder}")
    print("\n")

    # What is your desired backups_folder?
    # [0] "~/.phishpicks"
    # [1] "~/.phishpicks_backups"
    # OR Manually enter a backups_folder
    print("Backups Folder")
    print(f"[0] {Configuration.model_fields['backups_folder'].default}")
    print(f"[1] ~/.phishpicks")
    print("OR Manually enter a backups_folder")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > backups_folder > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['', '0']:
        backups_folder = Configuration.model_fields['backups_folder'].default
    elif user_input in ['1']:
        backups_folder = "~/.phishpicks"
    else:
        backups_folder = user_input
    print(f"Backups Folder set to {backups_folder}")
    print("\n")

    # What is your media_player_path
    # [0] "C://Program Files (x86)//Winamp//winamp.exe"
    # OR Manually enter a media_player_path
    print("Media Player Path")
    print(f"[0] {Configuration.model_fields['media_player_path'].default}")
    print("OR Manually enter a media_player_path")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > media_player_path > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['', '0']:
        media_player_path = Configuration.model_fields['media_player_path'].default
    else:
        media_player_path = user_input
    print(f"Backups Folder set to {media_player_path}")
    print("\n")

    # Print all the attributes in Configuration
    # Confirm?
    # Yes / No
    # Yes, save_to_json
    # No, exit
    print("Confirm these Configuration Settings?")
    print(f"Phish Folder set to {phish_folder}")
    print(f"Show Glob Format set to: {show_glob}")
    print(f"Configuration Folder set to {config_folder}")
    print(f"Backups Folder set to {backups_folder}")
    print(f"Backups Folder set to {media_player_path}")
    print("\n")
    print("Confirm? [Y]")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > configuration > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['y', 'Y']:
        print("Writing Configuration")
        config = Configuration(config_folder=config_folder,
                               backups_folder=backups_folder,
                               phish_folder=phish_folder,
                               media_player_path=media_player_path,
                               show_glob=show_glob,
                               venue_regex=venue_regex)
        return config
    else:
        print('Unconfigured, exiting...')
        return None


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


class DataMenuCompleter(Completer):

    def __init__(self, methods):
        self.methods = methods

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        pass


def main():
    config = configuration_flow()
    db = PhishData(config=config)
    pick = PhishPicks(db=db, config=config)
    db.restore_all()
    repl = PhishREPL(pick=pick)
    repl.start()
