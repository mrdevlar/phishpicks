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
    dap_path: str = None
    free: int = 0

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

    def connect(self):
        if self.pp.config.is_dap_folder():
            # pdb.set_trace()
            self.on_dap = PhishSelection()
            self.shows_on_dap()
            self.free_space()
            # print(f"{self.free} bytes free")
        else:
            raise RuntimeError(f"No Device at '{self.pp.config.dap_folder}'. Digital Audio Player Is Not Configured or Connected!")

    def shows_on_dap(self):
        self.on_dap.clear()
        shows = []
        for folder in Path(self.pp.config.dap_folder).glob(self.pp.config.show_glob):
            show_date = re.findall(r'\d\d\d\d-\d\d-\d\d', folder.name)[0]
            show = self.pp.db.show_by_date(show_date)
            shows.append(show)
        self.on_dap.extend(shows)

    def pick_random_show(self, k: int = 1, exclude_played: bool = True):
        if self.on_dap:
            on_dap_show_ids = [show.show_id for show in self.on_dap]
        else:
            on_dap_show_ids = None
        self.pp.random_shows(k=k, exclude_played=exclude_played, exclude_show_ids=on_dap_show_ids)

    def copy_to_dap(self):
        if self.free > self.pick_size():
            for pick in self.pp.picks:
                folder_src = str(Path(self.pp.config.phish_folder) / pick.folder_path)
                folder_des = str(Path(self.pp.config.dap_folder) / pick.folder_path)
                print(f"Copying to {folder_des}")
                shutil.copytree(folder_src, folder_des, dirs_exist_ok=True)
                self.pp.db.update_played_show(pick.date)
            self.pp.clear()
            self.shows_on_dap()
            self.free_space()
        else:
            raise OSError("Insufficient Disk Space")

    def dap_to_picks(self):
        self.pp.mode = 'shows'
        for pick in self.on_dap:
            self.pp.picks.append(pick)

    def update_played(self):
        self.pp.to_update()

    def last_copied_to_dap(self, last_n: int = 1):
        self.pp.last_played_shows(last_n=last_n)

    def select_on_dap(self, match: str):
        mode = 'shows'
        return self.on_dap.subselect(match, mode)

    def clear_dap(self):
        for sel in self.on_dap:
            dap_show = Path(self.pp.config.dap_folder) / Path(sel.folder_path)
            print(f"Deleting {dap_show}")
            shutil.rmtree(dap_show)
        self.shows_on_dap()

    def delete_from_dap(self, match: str = "", confirm: bool = True):
        selection = self.select_on_dap(match)
        for sel in selection:
            dap_show = Path(self.pp.config.dap_folder) / Path(sel.folder_path)
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

    def free_space(self):
        _, _, self.free = shutil.disk_usage(self.pp.config.dap_folder)

    def pick_size(self):
        size = 0
        for pick in self.pp.picks:
            folder = Path(self.pp.config.phish_folder) / pick.folder_path
            size += sum([file.stat().st_size for file in folder.glob('**/*')])
        return size
