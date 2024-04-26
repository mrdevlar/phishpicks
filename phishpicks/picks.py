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
            return f"Selected Shows\n{'\n'.join(self.picks)}"

    def random(self, k=1):
        all_shows = self.db.all_shows()
        self.picks = random.choices(all_shows, k=k)

    def play(self):
        raise NotImplementedError

    def enqueue(self):
        raise NotImplementedError

    def dap_copy(self):
        raise NotImplementedError


def main():
    winamp = Path("C:\Program Files (x86)\Winamp\winamp.exe")
    phish_folder = Path("Z:\Music\Phish")

    possible_folders = [folder for folder in phish_folder.glob("Phish [0-9]*")]
    selected_folder = random.choice(possible_folders)
    print(selected_folder)
    enqueue = False
    enqueue_command = "/ADD " if enqueue else ""

    cmd = 'powershell -Command' + f"""& "{winamp}" {enqueue_command}"{selected_folder}" """
    print(cmd)

    args = shlex.split(cmd)
    process = subprocess.Popen(args,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE,
                               shell=True)  # Create subprocess
    # stdout, stderr = process.communicate(input=b'y\n')  # Run command and send input, then read output
    # process.terminate()
    # print(stdout)  # Print output
    # print(stderr)  # Print error output, if any


if __name__ == '__main__':
    main()
