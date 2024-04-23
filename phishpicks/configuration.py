from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from pydantic import BaseModel


class Configuration(BaseModel):
    config_file: str = "phishpicks.json"
    config_folder: str = str(Path(os.path.expanduser("~/.phishpicks")))
    phish_folder: str = str(Path("Z://Music//Phish"))
    phish_db: str = "phish.db"

    @staticmethod
    def from_json(config_file: str = "phishpicks.json",
                  config_folder: str = str(Path(os.path.expanduser("~/.phishpicks")))) -> Configuration:
        configuration_file = config_folder / Path(config_file)
        with open(configuration_file, 'r') as file:
            data = json.load(file)
        config = Configuration.parse_obj(data)
        print(config)
        return config

    def save_to_json(self):
        configuration_file = self.config_folder / Path(self.config_file)
        print(configuration_file)
        # Save JSON string to file
        with open(configuration_file, 'w') as file:
            conf_json = json.dumps(self.dict())
            file.write(conf_json)
            print(f"Wrote Config to {configuration_file}")

    def is_configured(self) -> bool:
        """ Checks if configuration exists and is complete """
        # Config Folder Exists?
        # DB Exists?
        # DB Tables Have Content?
        # Phish Folder Exists and has Folders?
        raise NotImplementedError

    def is_configuration_folder(self) -> bool:
        return self.config_folder.exists()

    def is_phish_folder(self) -> bool:
        return Path(self.phish_folder).exists()

    def is_db(self) -> bool:
        db_location = self.config_folder / Path(self.phish_db)
        return db_location.exists()

    def create_configuration_folder(self):
        Path(self.config_folder).mkdir(parents=False, exist_ok=True)

    def delete_configuration_folder(self):
        shutil.rmtree(self.config_folder)
        print(f'Deleted {self.config_folder}')

    def total_phish_folders(self):
        return len(list(Path(self.phish_folder).glob("Phish [0-9]*")))
