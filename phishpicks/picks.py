from __future__ import annotations
import random
import subprocess
import shlex
from pathlib import Path
from pydantic import BaseModel
from phishpicks import Configuration
from phishpicks import PhishData


class PhishPicks(BaseModel):
    db: PhishData
    config: Configuration
    picks: list = []

    @staticmethod
    def load(**kwargs) -> PhishPicks:
        config = Configuration.from_json(**kwargs)
        db = PhishData(config=config)
        return PhishPicks(db=db, config=config)

    def __repr__(self):
        """ Shows Summary of Phish Picks"""
        if not self.picks:
            total_shows = self.db.total_shows()
            return f"Total Shows: {total_shows}"
        else:
            selection = "__ Selected Shows __\n"
            selection += "\n".join([repr(x) for x in self.picks])
            return selection

    def random(self, k=1):
        all_shows = self.db.all_shows()
        self.picks = random.choices(all_shows, k=k)

    def play(self, update=True):
        if len(self.picks) == 1:
            media_player = Path(self.config.media_player_path)
            pick_folder = Path(self.picks[0].folder_path)
            pick_folder = Path(self.config.phish_folder) / pick_folder
            cmd = 'powershell -Command' + f"""& "{media_player}" "{pick_folder}" """
            if update:
                # Add times played to db
                self.db.update_show(show_id=self.picks[0].show_id)
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


# pp = PhishPicks.load()
# pp.random()
# pp.play()
# print(pp)

