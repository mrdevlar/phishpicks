# Digital Audio Player Controls
import re
import shutil
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from phishpicks import PhishPicks, PhishSelection


class PhishDAP(BaseModel):
    pp: PhishPicks
    on_dap: Any = None
    dap_path: str = str(Path('E:\\01_Phish'))  # @TODO: Replace with pp.config
    date_re: str = r'\d\d\d\d-\d\d\-\d\d'

    def __repr__(self):
        selection = ""
        if self.on_dap:
            selection += f"_______ On Digital Audio Player _______\n"
            selection += "\n".join([repr(x) for x in self.on_dap])
        else:
            selection += "\n___ Digital Audio Player is Empty! ___\n"
        if self.pp.picks:
            selection += f"\n_________ Phish Picks _________\n"
            selection += "\n".join([repr(x) for x in self.pp.picks])
        else:
            selection += "\n_______ No Picks Present _______"
        return selection

    def model_post_init(self, __context: Any) -> None:
        if not Path(self.dap_path).exists():
            raise RuntimeError(f"No Device at {self.dap_path}! Digital Audio Player Is Not Configured or Connected")
        self.on_dap = PhishSelection()
        self.shows_on_dap()

    def shows_on_dap(self):
        self.on_dap.clear()
        shows = []
        for folder in Path(self.dap_path).glob(self.pp.config.show_glob):
            show_date = re.findall(self.date_re, folder.name)[0]
            show = self.pp.db.show_by_date(show_date)
            shows.append(show)
        self.on_dap.extend(shows)

    def pick_random_show(self, k: int = 1, exclude_played: bool = False):
        if self.on_dap:
            on_dap_show_ids = [show.show_id for show in self.on_dap]
        else:
            on_dap_show_ids = None
        self.pp.random_shows(k=k, exclude_played=exclude_played, exclude_show_ids=on_dap_show_ids)

    def copy_to_dap(self):
        # @TODO: Will it fit? If not, fail
        for pick in self.pp.picks:
            folder_src = str(Path(self.pp.config.phish_folder) / pick.folder_path)
            folder_des = str(Path(self.dap_path) / pick.folder_path)
            print(f"Copying to {folder_des}")
            shutil.copytree(folder_src, folder_des, dirs_exist_ok=True)
        self.pp.clear()
        self.shows_on_dap()

    def select_on_dap(self, match: str):
        mode = 'shows'
        return self.on_dap.subselect(match, mode)

    def clear_dap(self):
        for sel in self.on_dap:
            dap_show = Path(self.dap_path) / Path(sel.folder_path)
            print(f"Deleting {dap_show}")
            shutil.rmtree(dap_show)
        self.shows_on_dap()

    def delete_from_dap(self, match: str = "", confirm: bool = True):
        selection = self.select_on_dap(match)
        for sel in selection:
            dap_show = Path(self.dap_path) / Path(sel.folder_path)
            assert dap_show.exists(), "Show does not exist"
            assert dap_show.is_dir(), "Show is not a folder"
            try:
                if confirm:
                    response = input(f"Delete {dap_show}? - [y/n]")
                    if response.lower().strip() == 'n':
                        print("Not Deleted")
                        continue
                    elif response.lower().strip() == 'y':
                        shutil.rmtree(dap_show)
                    else:
                        raise ValueError("response must be in {y,n}")
                else:
                    shutil.rmtree(dap_show)
            except OSError as e:
                print(f"Error Deleting Folder: {e}")
            else:
                print(f"Show {dap_show} has been successfully deleted.")
        self.shows_on_dap()


pp = PhishPicks.load()
dp = PhishDAP(pp=pp)
# dp.clear_dap()
dp.pick_random_show(3)
dp.copy_to_dap()
print(dp)
