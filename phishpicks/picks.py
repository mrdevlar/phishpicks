from __future__ import annotations
import random
import re
import subprocess
import shlex
from pathlib import Path
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from phishpicks import Configuration
from phishpicks import PhishData


class PhishList(list):
    def __init__(self, *args):
        super(PhishList, self).__init__(*args)
        self._map = set()

    def __repr__(self):
        return "\n".join([repr(x) for x in self])

    def extend(self, new_elements):
        new_elements = [element for element in new_elements if element not in self._map]
        self._map.update(new_elements)
        super(PhishList, self).extend(new_elements)
        self.sort()
        print("\n".join([repr(x) for x in self]))

    def append(self, new_element):
        if new_element in self._map:
            print("\n".join([repr(x) for x in self]))
        else:
            self._map.add(new_element)
            super(PhishList, self).append(new_element)
            self.sort()
            print("\n".join([repr(x) for x in self]))

    def clear(self):
        super(PhishList, self).clear()
        self._map.clear()


class PhishPicks(BaseModel):
    db: PhishData
    config: Configuration
    _picks: PhishList = None
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
        self.picks = PhishList()

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
        config = Configuration.from_json(**kwargs)
        db = PhishData(config=config)
        return PhishPicks(db=db, config=config)

    def clear(self):
        self.picks.clear()

    def random(self, k=1):
        self.mode = 'shows'
        all_shows = self.db.all_shows()
        selected_shows = random.choices(all_shows, k=k)
        self.picks.extend(selected_shows)

    def all_shows(self):
        self.mode = 'shows'
        all_shows = self.db.all_shows()
        self.picks.extend(all_shows)

    def pick_show(self, date):
        self.mode = 'show'
        selected_show = self.db.show_by_date(date)
        self.picks.append(selected_show)

    def shows(self, keep_tracks: bool = False):
        """
        Args:
            keep_tracks: Show tracks also? (Default: False)
        """
        if self._mode == 'shows':
            print("\n".join([repr(x) for x in self.picks]))
        if not self.picks:
            raise ValueError("No tracks selected")
        else:
            show_tracks = self.db.shows_from_tracks(self.picks)
            for show in show_tracks:
                print(repr(show))
                if keep_tracks:
                    for track in self.picks:
                        if show.show_id == track.show_id:
                            print(f"\t{repr(track)}")

    def to_shows(self):
        if self._mode == 'tracks':
            show_tracks = self.db.shows_from_tracks(self.picks)
            self.mode = 'shows'
            self.picks.extend(show_tracks)
        elif self._mode == 'shows':
            print("\n".join([repr(x) for x in self.picks]))
        else:
            raise ValueError("Unknown mode")

    def pick_track(self, date_string: str, name: str, exact=False):
        show, track = self.db.track_by_date_name(date_string, name, exact)
        self.picks.append(track)
        self.mode = 'tracks'

    def tracks(self):
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
        if self._mode == 'shows':
            show_tracks = self.db.tracks_from_shows(self.picks)
            self.mode = 'tracks'
            self.picks.extend(show_tracks)
        elif self._mode == 'tracks':
            print("\n".join([repr(x) for x in self.picks]))
        else:
            raise ValueError("Unknown mode")

    def all_special(self):
        special_tracks = self.db.all_special_tracks()
        if self._mode == 'shows':
            self.mode = 'tracks'
        elif self._mode == 'tracks':
            pass
        else:
            raise ValueError('Unknown mode')
        self.picks.extend(special_tracks)

    def to_special(self):
        if self._mode == 'shows':
            raise NotImplementedError("to_special is not available in 'shows' mode")
        elif self._mode == 'tracks':
            [self.db.update_special_track(track) for track in self._picks]
        else:
            raise ValueError('Unknown mode')

    @staticmethod
    def extract_date(select_statement):
        """ Extracts the date from the selection statement """
        # Regular expression to match a date in format YYYY-MM-DD
        # @TODO: Move to UI
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

    def play(self, update=True):
        if len(self.picks) == 1:
            media_player = Path(self.config.media_player_path)
            pick_folder = Path(self.picks[0].folder_path)
            pick_folder = Path(self.config.phish_folder) / pick_folder
            cmd = 'powershell -Command' + f"""& "{media_player}" "{pick_folder}" """
            if update:
                # Add times played to db
                self.db.update_played_show(show_id=self.picks[0].show_id)
            print(cmd)
            args = shlex.split(cmd)
            process = subprocess.Popen(args,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE,
                                       shell=True)
        else:
            raise ValueError("Too many shows selected")

    def enqueue(self):
        enqueue = False
        enqueue_command = "/ADD " if enqueue else ""
        raise NotImplementedError

    def dap_copy(self):
        raise NotImplementedError


# def main():
#     pp = PhishPicks.load()
#     pp.random()
#     pp.play()
# pp = PhishPicks.load()
# pp.random()
# pp.random()
# pp.tracks()
# pp.to_tracks()
# pp.pick_track("2023-09-02", "Ghost")
# pp.clear()
# date, track = pp.extract_date("2019-07-14 Mercury")
# pp.pick_track(date, track, exact=False)
# pp.to_special()
# pp.pick_track("2012-06-29", "Possum")
# pp.shows()
# print(pp)
# pp.play()
# print(pp)
