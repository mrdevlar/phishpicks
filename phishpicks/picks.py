from __future__ import annotations
import json
import re
import subprocess
import shlex
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from phishpicks import Configuration
from phishpicks import PhishData


class PhishSelection(list):
    """ Special list for holding picks, these can be shows or tracks """
    def __init__(self, *args):
        super(PhishSelection, self).__init__(*args)
        self._map = set()

    def __repr__(self):
        return "\n".join([repr(x) for x in self])

    def extend(self, new_elements):
        new_elements = [element for element in new_elements if element not in self._map]
        self._map.update(new_elements)
        super(PhishSelection, self).extend(new_elements)
        self.sort()
        print("\n".join([repr(x) for x in self]))

    def append(self, new_element):
        if new_element in self._map:
            print("\n".join([repr(x) for x in self]))
        else:
            self._map.add(new_element)
            super(PhishSelection, self).append(new_element)
            self.sort()
            print("\n".join([repr(x) for x in self]))

    def subselect(self, match: str, mode: str, verbose: bool = False):
        # @TODO: Fix Repr Error
        if len(self) == 0:
            raise ValueError('Nothing is picked')
        if mode not in ['shows', 'tracks']:
            raise TypeError("mode must be one of {'shows', 'tracks'}")
        selected_list = PhishSelection()
        for pick in self:
            pick_data = pick.folder_path if mode == 'shows' else pick.file_path
            if re.search(match, pick_data, re.IGNORECASE):
                selected_list.append(pick)
        if verbose:
            print("\n".join([repr(x) for x in selected_list]))
        return selected_list

    def delete(self, match: str, mode: str, verbose: bool = False):
        # @TODO: Fix Repr Error
        selection = self.subselect(match=match, mode=mode)
        if verbose:
            print("Deleting...")
            print("\n".join([repr(x) for x in selection]))
        for sel in selection:
            super(PhishSelection, self).remove(sel)
            self._map.remove(sel)

    def clear(self):
        super(PhishSelection, self).clear()
        self._map.clear()


class PhishPicks(BaseModel):
    db: PhishData
    config: Configuration
    _picks: PhishSelection = None
    _mode: str = None

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        if value in ['shows', 'tracks']:
            if value != self._mode:
                self.clear()
            self._mode = value
        else:
            raise TypeError("mode must be one of {'shows', 'tracks'}")

    @property
    def picks(self):
        return self._picks

    @picks.setter
    def picks(self, value):
        self._picks = value

    def model_post_init(self, __context: Any) -> None:
        self.picks = PhishSelection()

    def __repr__(self):
        """ Shows Summary of Phish Picks"""
        if not self.picks:
            total_shows = self.db.total_shows()
            return f"Total Shows: {total_shows}"
        else:
            selection = f"__ Selected {self.mode.title()} __\n"
            selection += "\n".join([repr(x) for x in self.picks])
            return selection

    @staticmethod
    def load(**kwargs) -> PhishPicks:
        """
        Initializes Phishpicks
        Args:
            **kwargs: keyword arguments to be passed to the Configuration
        """
        config = Configuration(**kwargs)
        if config.is_configuration_file():
            config = Configuration.from_json(**kwargs)
        else:
            config.configure()
        db = PhishData(config=config)
        return PhishPicks(db=db, config=config)

    def clear(self):
        """ Clears the contents of the picks """
        self.picks.clear()

    def random_shows(self, k: int = 1, exclude_played: bool = True, exclude_show_ids: list = None):
        """
        Randomly adds k shows to picks
        Args:
            k: the number of shows to randomly select
            exclude_played: exclude all times_played > 0
            exclude_show_ids: exclude a list of show_ids
        """
        self.mode = 'shows'
        selected_shows = self.db.random_shows(k=k, exclude_played=exclude_played, exclude_show_ids=exclude_show_ids)
        self.picks.extend(selected_shows)

    def random_tracks(self, k: int = 1):
        """
        Randomly adds k tracks to picks
        Args:
            k: the number of tracks to randomly select
        """
        self.mode = 'tracks'
        selected_tracks = self.db.random_tracks(k=k)
        self.picks.extend(selected_tracks)

    def all_shows(self):
        """ Adds all shows to picks """
        self.mode = 'shows'
        all_shows = self.db.all_shows()
        self.picks.extend(all_shows)

    def last_played_shows(self, last_n: int = 1):
        self.mode = 'shows'
        last_played = self.db.last_played_shows(last_n=last_n)
        self.picks.extend(last_played)

    def pick_show(self, date: str):
        """
        Adds a selected show to picks
        Args:
            date: Date string in 'YYYY-MM-DD' format
        """
        self.mode = 'shows'
        selected_show = self.db.show_by_date(date)
        self.picks.append(selected_show)

    def shows(self, keep_tracks: bool = False):
        """
        Displays the shows corresponding to tracks
        Args:
            keep_tracks: Show tracks also? (Default: False)
        """
        if self._mode == 'shows':
            print("\n".join([repr(x) for x in self.picks]))
        if not self.picks:
            raise ValueError("No tracks selected")
        else:
            show_tracks = self.db.shows_from_tracks(self.picks)
            show_tracks.sort()
            for show in show_tracks:
                print(repr(show))
                if keep_tracks:
                    for track in self.picks:
                        if show.show_id == track.show_id:
                            print(f"\t{repr(track)}")

    def to_shows(self):
        """ Converts the tracks in picks into shows """
        if self._mode == 'tracks':
            show_tracks = self.db.shows_from_tracks(self.picks)
            self.mode = 'shows'
            self.picks.extend(show_tracks)
        elif self._mode == 'shows':
            print("\n".join([repr(x) for x in self.picks]))
        else:
            raise ValueError("Unknown mode")

    def pick_track(self, show_date: str, track_name: str, exact=False):
        """
        Adds a selected track to picks
        Args:
            show_date: Date string in 'YYYY-MM-DD' format
            track_name: A partial name of track
            exact: Do you want an exact match?
        """
        self.mode = 'tracks'
        show, track = self.db.track_by_date_name(show_date, track_name, exact)
        self.picks.append(track)

    def pick_tracks_by_name(self, track_name: str, exact=False):
        self.mode = 'tracks'
        tracks = self.db.tracks_by_name(track_name, exact)
        self.picks.extend(tracks)

    def tracks(self):
        """ Displays the tracks corresponding to the shows in picks """
        if self._mode == 'tracks':
            print("\n".join([repr(x) for x in self.picks]))
        if not self.picks:
            raise ValueError("No shows selected")
        else:
            show_tracks = self.db.tracks_from_shows(self.picks)
            for show in self.picks:
                print(repr(show))
                for track in show_tracks:
                    if track.show_id == show.show_id:
                        print(f"\t{repr(track)}")

    def to_tracks(self):
        """ Converts the shows to tracks in picks """
        if self._mode == 'shows':
            show_tracks = self.db.tracks_from_shows(self.picks)
            self.mode = 'tracks'
            self.picks.extend(show_tracks)
        elif self._mode == 'tracks':
            print("\n".join([repr(x) for x in self.picks]))
        else:
            raise ValueError("Unknown mode")

    def all_special(self):
        """ Adds all special tracks to picks """
        special = []
        if self._mode == 'tracks':
            special = self.db.all_special_tracks()
        elif self._mode == 'shows':
            special = self.db.all_special_shows()
        else:
            print("Special must be selected from show or track mode")
        self.picks.extend(special)

    def to_special(self):
        """ Adds all tracks in picks to special tracks """
        if self._mode == 'shows':
            [self.db.update_special_show(show) for show in self._picks]
        elif self._mode == 'tracks':
            [self.db.update_special_track(track) for track in self._picks]
        else:
            raise ValueError('Unknown mode')

    def to_update(self):
        if self._mode == 'tracks':
            raise NotImplementedError("to_update is not available in 'tracks' mode")
        elif self._mode == 'shows':
            for show in self._picks:
                self.db.update_played_show(show.date)
        else:
            raise ValueError('Unknown mode')

    def reset_last_played(self):
        """ Returns last_played to None and times_played to 0 """
        if self._mode == 'shows':
            [self.db.reset_played_shows(track) for track in self._picks]
        elif self._mode == 'tracks':
            raise NotImplementedError("reset_last_played only available in 'shows' mode")
        else:
            raise ValueError('Unknown mode')

    def save_queue(self):
        if self._mode != 'shows':
            raise ValueError('Only available in shows mode')
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('picks_queue.json')
        backup_list = [show.date.strftime('%Y-%m-%d') for show in self._picks]
        with open(backup_json, 'w') as file:
            json.dump(backup_list, file)
        print(f"Wrote Queue Backup to {backup_json}")

    def load_queue(self):
        self.mode = 'shows'
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('picks_queue.json')
        if not backup_json.exists():
            raise FileNotFoundError("'picks_queue.json' is not found")
        else:
            with open(backup_json, 'r') as file:
                backup_list = json.load(file)
            ps = PhishSelection()
            for show_date in backup_list:
                self.pick_show(show_date)

    def subselect(self, match: str, verbose: bool = False):
        self.picks.subselect(match, self._mode, verbose)

    def play(self, enqueue: bool = False, update: bool = True):
        """
        Plays the selected picks with your media player
        Args:
            enqueue: Do you want to enqueue, rather than replace, to the playlist?
            update: Do you want to update time last played?
        """
        if self._mode == 'shows':
            picks_folders = [str(Path(self.config.phish_folder)) + "\\" + pick.folder_path for pick in self.picks]
        elif self._mode == 'tracks':
            picks_folders = [pick.file_path for pick in self.picks]
        else:
            raise ValueError('Unknown mode')
        media_player = Path(self.config.media_player_path)
        sep = '" "'
        add = " /ADD " if enqueue else " "
        cmd = 'powershell -Command' + f"""& "{media_player}"{add}"{sep.join(picks_folders)}" """
        if update and self._mode == 'shows':
            # Add times played to db
            [self.db.update_played_show(pick.date.strftime('%Y-%m-%d')) for pick in self.picks]
        print(cmd)
        args = shlex.split(cmd)
        process = subprocess.Popen(args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   shell=True)

# def main():
#     pp = PhishPicks.load()
#     pp.random()
#     pp.play()
# pp = PhishPicks.load()
# pp.random()
# pp.random()
# pp.play()
# pp.tracks()
# pp.to_tracks()
# pp.pick_track("2023-09-02", "Ghost")
# pp.pick_track("2019-07-14", "Mercury")
# pp.play()
# pp.clear()
# date, track = pp.extract_date("2019-07-14 Mercury")
# pp.pick_track(date, track, exact=False)
# pp.to_special()
# pp.pick_track("2012-06-29", "Possum")
# pp.shows()
# print(pp)
# pp.play()
# print(pp)
