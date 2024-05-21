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
    dap_path: str = str(Path('E:\\01_Phish'))
    date_re: str = r'\d\d\d\d-\d\d\-\d\d'

    def __repr__(self):
        selection = ""
        if self.on_dap:
            selection += f"_______ On Digital Audio Player _______\n"
            selection += "\n".join([repr(x) for x in self.on_dap])
        else:
            selection += "Digital Audio Player is Empty!\n"
        if self.pp.picks:
            selection += f"\n_________ Phish Picks _________\n"
            selection += "\n".join([repr(x) for x in self.pp.picks])
        else:
            selection += "No Picks Present"
        return selection

    def model_post_init(self, __context: Any) -> None:
        if not Path(self.dap_path).exists():
            raise RuntimeError("Digital Audio Player Is Not Configured or Connected")
        self.on_dap = PhishSelection()
        self.shows_on_dap()

    def shows_on_dap(self):
        shows = []
        for folder in Path(self.dap_path).glob(self.pp.config.show_glob):
            show_date = re.findall(self.date_re, folder.name)[0]
            show = self.pp.db.show_by_date(show_date)
            shows.append(show)
        self.on_dap.extend(shows)

    def select(self, match: str):
        mode = 'shows'
        return self.on_dap.subselect(match, mode)

    def random_show(self, k: int = 1, exclude_played: bool = False):
        if self.on_dap:
            on_dap_show_ids = [show.show_id for show in self.on_dap]
        else:
            on_dap_show_ids = None
        self.pp.random_shows(k=k, exclude_played=exclude_played, exclude_show_ids=on_dap_show_ids)

    def delete(self, match: str, confirm: bool = True):
        selection = self.select(match)
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
                        self.on_dap.remove(sel)
                        shutil.rmtree(dap_show)
                    else:
                        raise ValueError("response must be in {y,n}")
                else:
                    self.on_dap.remove(sel)
                    shutil.rmtree(dap_show)
            except OSError as e:
                print(f"Error Deleting Folder: {e}")
            else:
                print(f"Show {dap_show} has been successfully deleted.")


pp = PhishPicks.load()
dp = PhishDAP(pp=pp)
print(dp)
