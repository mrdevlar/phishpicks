from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from pydantic import BaseModel
from typing import Any


class Configuration(BaseModel):
    config_file: str = "phishpicks.json"
    config_folder: str = str(Path(os.path.expanduser("~/.phishpicks")))
    backups_folder: str = str(Path(os.path.expanduser("~/.phishpicks_backups")))
    phish_folder: str = str(Path("Z://Music//Phish"))
    media_player_path: str = str(Path("C://Program Files (x86)//Winamp//winamp.exe"))
    phish_db: str = "phish.db"
    show_glob: str = "Phish [0-9]*"
    venue_regex: str = r'Phish \d\d\d\d-\d\d-\d\d (.*?.*)'
    dap_folder: str = str(Path("E://01_Phish"))
    configured: dict = None

    def __repr__(self):
        is_config = self.is_configured()
        if is_config:
            return BaseModel.__repr__(self)
        else:
            for key, value in self.configured.items():
                print(f"{key!s:>25}: {value}")
            return BaseModel.__repr__(self)

    def model_post_init(self, __context: Any):
        is_config = self.is_configured()

    @staticmethod
    def from_json(config_file: str = "phishpicks.json",
                  config_folder: str = str(Path(os.path.expanduser("~/.phishpicks"))),
                  **kwargs) -> Configuration:
        configuration_file = config_folder / Path(config_file)
        with open(configuration_file, 'r') as file:
            data = json.load(file)
        config = Configuration.model_validate(data)
        return config

    def save_to_json(self):
        configuration_file = self.config_folder / Path(self.config_file)
        print(configuration_file)
        # Save JSON string to file
        with open(configuration_file, 'w') as file:
            conf_json = json.dumps(self.model_dump())
            file.write(conf_json)
            print(f"Wrote Config to {configuration_file}")

    def is_configured(self) -> bool:
        """ Checks if configuration exists and is complete """
        self.configured = {'is_configuration_folder': self.is_configuration_folder(),
                           'is_configuration_file': self.is_configuration_file(),
                           'is_db': self.is_db(),
                           'is_backups_folder': self.is_backups_folder(),
                           'is_media_player': self.is_media_player(),
                           'is_phish_folder': self.is_phish_folder()}
        is_config = all([values for values in self.configured.values()])
        return is_config

    def is_configuration_file(self) -> bool:
        return (Path(self.config_folder) / Path(self.config_file)).exists()

    def is_configuration_folder(self) -> bool:
        return Path(self.config_folder).exists()

    def is_backups_folder(self) -> bool:
        return Path(self.backups_folder).exists()

    def is_db(self) -> bool:
        db_location = self.config_folder / Path(self.phish_db)
        return db_location.exists()

    def is_media_player(self) -> bool:
        return Path(self.media_player_path).exists()

    def is_phish_folder(self) -> bool:
        return Path(self.phish_folder).exists()

    def is_dap_folder(self) -> bool:
        return Path(self.phish_folder).exists()

    def create_configuration_folder(self):
        Path(self.config_folder).mkdir(parents=True, exist_ok=True)

    def create_backups_folder(self):
        Path(self.backups_folder).mkdir(parents=True, exist_ok=True)

    def create_configure_db(self):
        # Might be tight coupling...
        from phishpicks import PhishData
        db = PhishData(config=self)
        db.create()
        db.populate()
        db.engine.dispose()
        db.restore_all()
        return db

    def delete_configuration_folder(self):
        shutil.rmtree(self.config_folder)
        print(f'Deleted {self.config_folder}')

    def total_phish_folders(self) -> int:
        return len(list(Path(self.phish_folder).glob(self.show_glob)))

    def total_phish_songs(self) -> int:
        """ Counts the total number of songs in the Phish folder """
        return len(list(Path(self.phish_folder).glob(f"{self.show_glob}/*.[fFmM][lLpP4][3aA]*")))

    def configure(self):
        if not self.configured['is_phish_folder']:
            raise FileNotFoundError("Phish folder not found")
        if not self.configured['is_media_player']:
            raise FileNotFoundError("Media player not found")
        if not self.configured['is_backups_folder']:
            self.create_backups_folder()
        if not self.configured['is_configuration_folder']:
            self.create_configuration_folder()
        if not self.configured['is_configuration_file']:
            self.save_to_json()
        if not self.configured['is_db']:
            return self.create_configure_db()
