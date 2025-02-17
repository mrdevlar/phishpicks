from __future__ import annotations
import re
from datetime import datetime
from typing import Callable, Iterable, Any
from phishpicks import Configuration, PhishData, PhishPicks
from pydantic import BaseModel
from prompt_toolkit.completion import WordCompleter, CompleteEvent, Completion
from prompt_toolkit.completion import Completer
from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML


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
            # This allows for testing of PhishREPL
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
        show_completer = self.pick.db.all_show_dates()
        show_completer.extend(
            ['random', 'last_played', 'load_queue', 'save_queue', 'play', 'clear', 'help', 'tracks', 'to_tracks',
             'to_update', 'reset_last_played', 'to_special', 'exit'])
        completer = WordCompleter(show_completer, WORD=True)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > shows > </style>')
        placeholder = HTML('<style color="#6A87A0">YYYY-MM-DD</style>')
        user_input = self.session.prompt(prompt_text, placeholder=placeholder, completer=completer,
                                         complete_while_typing=True, key_bindings=self.kb)
        if not user_input:
            print(repr(self.pick))
        elif user_input.startswith('random'):
            random_split = user_input.rstrip().split(" ")
            if len(random_split) == 1:
                self.pick.random_shows()
                print(repr(self.pick))
            if len(random_split) == 2:
                n = random_split[1]
                self.pick.random_shows(n)
                print(repr(self.pick))
            else:
                print('"random %n%" is supported')
        # @TODO: Add yrandom : random_by_year
        elif user_input == 'load_queue':
            self.pick.load_queue()
            print(repr(self.pick))
        elif user_input == 'save_queue':
            self.pick.save_queue()
        elif user_input == 'play':
            self.pick.play()
        elif user_input == 'last_played':
            #@TODO: Add #n
            self.pick.last_played_shows()
            print(repr(self.pick))
        elif user_input == 'clear':
            self.pick.clear()
        elif user_input == 'help':
            self.help_menu()
        elif user_input == 'tracks':
            self.pick.tracks()
        elif user_input == 'to_update':
            self.pick.to_update()
        elif user_input == 'reset_last_played':
            self.pick.reset_last_played()
        elif user_input == 'to_tracks':
            self.pick.to_tracks()
            self.menu = 'tracks'
            print(repr(self.pick))
        elif user_input == 'to_special':
            if self.pick.mode == 'shows':
                self.pick.to_special()
                self.pick.db.backup_show_special()
            else:
                print('No shows in picks')
        elif user_input == 'exit':
            raise KeyboardInterrupt
        else:
            selected_show, _ = self.extract_date(user_input)
            if not selected_show:
                print("Incomplete Date, Try Again")
            else:
                self.pick.pick_show(user_input.strip())
                print(repr(self.pick))

    def tracks_menu(self):
        date_completer = self.pick.db.all_show_dates()
        completer = DateTrackCompleter(date_completer, self.pick.db.tracks_from_date)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > tracks > </style>')
        placeholder = HTML('<style color="#6A87A0">YYYY-MM-DD TRACK_NAME</style>')
        user_input = self.session.prompt(prompt_text, placeholder=placeholder, completer=completer,
                                         complete_while_typing=True, key_bindings=self.kb)
        if not user_input:
            print(repr(self.pick))
        elif user_input.startswith('random'):
            random_split = user_input.rstrip().split(" ")
            if len(random_split) == 1:
                self.pick.random_tracks()
                print(repr(self.pick))
            if len(random_split) == 2:
                n = random_split[1]
                self.pick.random_tracks(n)
                print(repr(self.pick))
            else:
                print('"random %n%" is supported')
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
            print(repr(self.pick))
        elif user_input == 'to_special':
            if self.pick.mode == 'tracks':
                self.pick.to_special()
                self.pick.db.backup_track_special()
            else:
                print('No tracks in picks')
            print(repr(self.pick))
        elif user_input == 'specials':
            self.pick.mode = 'tracks'
            self.pick.all_special()
            print(repr(self.pick))
        elif user_input == 'exit':
            raise KeyboardInterrupt
        else:
            show_date, track_name = self.extract_date(user_input)
            if not show_date or not track_name:
                print("Missing Values, Try Again")
            else:
                self.pick.pick_track(show_date, track_name, exact=True)
                print(repr(self.pick))

    def data_menu(self):
        all_data_methods = [func for func in dir(PhishData)
                            if callable(getattr(PhishData, func)) and not func.startswith('_')]
        # @TODO: Replace with function completer
        data_completer = WordCompleter(all_data_methods, ignore_case=True, WORD=True)
        prompt_text = HTML('<style color="#FFDC00">phishpicks > data > </style>')
        placeholder = HTML('<style color="#6A87A0">PhishData Method</style>')
        user_input = self.session.prompt(prompt_text, placeholder=placeholder, completer=data_completer,
                                         complete_while_typing=True, key_bindings=self.kb)
        user_input_list = user_input.rstrip().split(" ")
        method_name = user_input_list.pop(0)
        if method_name == 'help':
            self.help_menu()
        elif method_name in all_data_methods:
            method = getattr(self.pick.db, method_name)
            if user_input_list:
                print(method(*user_input_list))
            else:
                print(method())
        else:
            print('data method not found')

    def dap_menu(self):
        from phishpicks import PhishDAP  # @TODO: Fix import

        dap_completer = WordCompleter(
            ['random', 'copy', 'clear_picks', 'clear_dap', 'dap_to_picks', 'last_copied', 'free_space', 'del'],
            ignore_case=True, WORD=True)
        try:
            dap = PhishDAP(pp=self.pick)
            dap.connect()

            prompt_text = HTML('<style color="#FFDC00">phishpicks > dap > </style>')
            placeholder = HTML('<style color="#6A87A0">Digital Audio Player Methods</style>')
            user_input = self.session.prompt(prompt_text, placeholder=placeholder, completer=dap_completer,
                                             complete_while_typing=True, key_bindings=self.kb)

            if not user_input:
                print(repr(dap))
            elif user_input == 'clear_picks' or user_input == 'clear':
                self.pick.clear()
                print(repr(dap))
            elif user_input == 'clear_dap':
                dap.clear_dap()
                print(repr(dap))
            elif user_input == 'copy':
                dap.copy_to_dap()
                print(repr(dap))
            elif user_input == 'dap_to_picks':
                dap.dap_to_picks()
                print(repr(dap))
            elif user_input == 'last_copied':
                dap.last_copied_to_dap()
                print(repr(dap))
            elif user_input == 'free_space':
                print(dap.free)
            elif user_input.startswith('del'):
                user_input_list = user_input.rstrip().split(" ")
                if len(user_input_list) == 0:
                    print('No match provided to delete')
                else:
                    delete_method = user_input_list.pop(0)
                    dap.delete_from_dap(user_input_list[0])
            elif user_input.startswith('random'):
                if user_input == 'random':
                    dap.pick_random_show()
                else:
                    user_input_list = user_input.rstrip().split(" ")
                    random_method = user_input_list.pop(0)
                    dap.pick_random_show(*user_input_list)
                print(repr(dap))
            elif user_input == 'help':
                self.help_menu()

        except RuntimeError as e:
            print(e)
            self.menu = 'main'

    def help_menu(self):
        speak_help = list()
        speak_help.append(" ")
        speak_help.append(" _____ COMMANDS _____ ")
        speak_help.append("      help: This List")
        speak_help.append("     shows: Select Shows")
        speak_help.append("    tracks: Select Tracks")
        speak_help.append("random %n%: Random Select N Picks")
        speak_help.append(" configure: Launch Configuration Wizard")
        speak_help.append("      data: Launch Database Operations")
        speak_help.append("       dap: Digital Audio Player Functions")
        speak_help.append("      play: Play Selection with Media Player")
        speak_help.append("     clear: Clear Picks")
        speak_help.append("      exit: Leave")
        speak_help.append(" ")
        speak_help.append(" _____ KEYBOARD _____ ")
        speak_help.append("Backspace: return to main menu / exit")
        speak_help.append("      Tab: cycle through autocomplete")
        speak_help.append("    Space: continues text")
        speak_help.append("    Enter: submits command")
        speak_help.append(" ")

        if self._menu == 'dap':
            speak_help.append("    _____ DAP COMMANDS _____ ")
            speak_help.append("       copy : Copy Picks to DAP")
            speak_help.append("   clear_dap: Delete ALL DAP Contents")
            speak_help.append(" clear_picks: Clear ALL Picks (same as regular clear)")
            speak_help.append(" del %match%: Delete from DAP specific match")
            speak_help.append("dap_to_picks: Load Picks List with DAP Content")
            speak_help.append(" last_copied: Load Picks with Last Copied Shows")
            speak_help.append("  free_space: Show Free Space on DAP")
            speak_help.append("  random %n%: Randomly Select N Shows")
            speak_help.append(" ")
        elif self._menu == 'shows':
            speak_help.append("      _____ SHOWS COMMANDS _____")
            speak_help.append(" load_queue: Load the Queue into Picks")
            speak_help.append(" save_queue: Save the Current Picks to Queue")
            speak_help.append("    tracks : Display the Tracks of the Selected Picks")
            speak_help.append("  to_tracks: Convert Show Picks to Track Picks")
            speak_help.append(" ")
        elif self._menu == 'tracks':
            speak_help.append("      _____ TRACKS COMMANDS _____  ")
            speak_help.append("      shows: Display the Shows of the Selected Picks")
            speak_help.append("   to_shows: Convert the Track Picks into Show Picks")
            speak_help.append("   specials: Load all Special Tracks into Picks")
            speak_help.append(" to_special: Mark track as Special")
            speak_help.append(" ")
        elif self._menu == 'data':
            all_data_methods = [func for func in dir(PhishData)
                                if callable(getattr(PhishData, func)) and not func.startswith('_')]
            speak_help.append(
                'NOTE : Data commands allow you to manipulate the underlying database that runs PhishPicks')
            speak_help.append("       This is expert mode, please see data.py for the operation of these commands")
            speak_help.append("   _____ DATA COMMANDS _____ ")
            speak_help.append("\n".join(all_data_methods))
            speak_help.append(" ")
        print("\n".join(speak_help))

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
                elif self._menu == 'clear':
                    self.pick.clear()
                    print(repr(self.pick))
                    self.menu = 'main'
                elif self._menu == 'play':
                    self.pick.play()
                    print(repr(self.pick))
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
                    print(repr(self.pick))
                elif self._menu == 'exit':
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                # @TODO: Random exit lyrics
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
    # [0] "C://Program Files//foobar2000//foobar2000.exe"
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

    # What is your dap_folder path?
    # [0] "E://01_Phish"
    # OR Manually enter a dap_folder
    print("Digital Audio Player Path")
    print(f"[0] {Configuration.model_fields['dap_folder'].default}")
    print("OR Manually enter a dap_folder")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > dap_folder > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['', '0']:
        dap_folder = Configuration.model_fields['dap_folder'].default
    else:
        dap_folder = user_input
    print(f"Digital Audio Player Path set to {dap_folder}")
    print("\n")

    # Enable Exhaustion Mode?
    print("Exhaustion Mode")
    print("Exhaustion Mode will exclude any shows that have been already played from random selection")
    print(f"[y] or Enter, Enable Exhaustion Mode")
    print(f"[n] Disable Exhaustion Mode")
    prompt_text = HTML('<style color="#FFDC00">phishpicks > configuration > exhaustion_mode > </style>')
    user_input = session.prompt(prompt_text, key_bindings=kb)
    if user_input in ['', 'y', 'Y']:
        exhaustion_mode = True
    else:
        exhaustion_mode = False
    print(f"Exhaustion Mode set to {exhaustion_mode}")
    print('\n')

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
    print(f"Digital Audio Player Path set to {dap_folder}")
    print(f"Exhaustion Mode set to {exhaustion_mode}")
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
                               venue_regex=venue_regex,
                               dap_folder=dap_folder,
                               exhaustion_mode=exhaustion_mode, )
        return config
    else:
        print('Unconfigured, exiting...')
        return None


class DateTrackCompleter(Completer):
    def __init__(self, date_completer: list, tracks_from_date: Callable):
        date_completer.extend(
            ['help', 'random', 'play', 'clear', 'shows', 'to_special', 'to_shows', 'specials', 'exit'])
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
