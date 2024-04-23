from __future__ import annotations
import re
import os
from os import PathLike
from pathlib import Path
from typing import Union
from pydantic import BaseModel
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Date, ForeignKey, Index, select
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
from datetime import date
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
import shutil
import json


# @TODO: Separate config from db


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
        self.config_folder.mkdir(parents=False, exist_ok=True)

    def delete_configuration_folder(self):
        shutil.rmtree(self.config_folder)
        print(f'Deleted {self.config_folder}')

    def create_db(self):
        self.create_configuration_folder()
        db_location = self.config_folder / Path(self.phish_db)
        print(db_location)
        engine = create_engine(f'sqlite:///{db_location}', echo=True)
        meta = MetaData()

        # define 'shows' table
        shows = Table(
            'shows', meta,
            Column('show_id', Integer, primary_key=True),
            Column('date', Date),
            Column('venue', String),
            Column('last_played', Date, nullable=True),
            Column('times_played', Integer, default=0),
            Column('folder_path', String)
        )

        # define 'tracks' table
        tracks = Table(
            'tracks', meta,
            Column('track_id', Integer, primary_key=True),
            Column('show_id', Integer, ForeignKey('shows.show_id')),
            Column('track_number', Integer),
            Column('name', String),
            Column('filetype', String),
            Column('length_sec', Integer),
            Column('file_path', String)
        )

        # create indexes
        Index('ix_shows_date', shows.c.date)
        Index('ix_shows_venue', shows.c.venue)
        Index('ix_shows_folder_path', shows.c.folder_path)
        Index('ix_tracks_name', tracks.c.name)
        Index('ix_tracks_file_path', tracks.c.file_path)
        # create all tables
        meta.create_all(engine)

    def populate_db(self):
        # Create engine and start session
        db_location = self.config_folder / Path(self.phish_db)
        print(db_location)
        engine = create_engine(f'sqlite:///{db_location}', echo=True)
        meta = MetaData()
        shows = Table('shows', meta, autoload_with=engine)
        tracks = Table('tracks', meta, autoload_with=engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        # Traverse folders and add show data to the shows table
        for folder in Path(self.phish_folder).glob("Phish [0-9]*"):
            # WindowsPath('Z:/Music/Phish/Phish 1989-08-26 Townshend, VT (LivePhish 09) [FLAC]')
            show_date = folder.name[6:16]
            venue_re = r'Phish \d\d\d\d-\d\d-\d\d (.*?.*)'
            show_venue = re.findall(venue_re, folder.name)
            show_venue = show_venue[0].strip() if show_venue else 'None'
            folder_path = folder.stem

            show_insert = shows.insert().values(date=date.fromisoformat(show_date),
                                                venue=show_venue,
                                                folder_path=folder_path)
            session.execute(show_insert)
            session.commit()

            show_id = session.query(shows.c.show_id).filter(shows.c.folder_path == folder_path).scalar()

            unsupported = []
            print(folder)
            for file in folder.glob("*.*"):
                file_path = str(file)
                track_filetype = file.suffix
                print(file)
                if file.suffix.lower() in ['.flac']:
                    audio = FLAC(file)
                    track_length_sec = int(audio.info.length)
                    track_name = audio.get('title')[0]
                    track_number = audio.get('tracknumber')[0]
                    print(file)
                elif file.suffix.lower() in ['.mp3']:
                    audio = MP3(file)
                    track_length_sec = int(audio.info.length)
                    track_name = audio.tags['TIT2'][0]
                    track_number = audio.tags['TRCK'][0]
                    print(file)
                elif file.suffix.lower() in ['.m4a']:
                    audio = MP4(file)
                    track_length_sec = int(audio.info.length)
                    track_name = audio.tags['©nam'][0]
                    track_number = audio.tags['trkn'][0][0]
                    print(file)
                else:
                    print(f"Unsupported File: {file}")
                    unsupported.append(str(file))
                    continue
                    # raise TypeError("Unsupported file format")

                track_insert = tracks.insert().values(
                    show_id=show_id,
                    track_number=track_number,
                    name=track_name,
                    filetype=track_filetype,
                    length_sec=track_length_sec,
                    file_path=file_path,
                )
                session.execute(track_insert)
                session.commit()

        # Close session
        session.close()
        print("Unsupported Files")
        print(unsupported)

    def query(self) -> list:
        db_location = self.config_folder / Path(self.phish_db)
        engine = create_engine(f'sqlite:///{db_location}', echo=True)

        metadata = MetaData()

        # shows = Table('shows', metadata, autoload_with=engine)
        table = Table('tracks', metadata, autoload_with=engine)
        columns = [column.name for column in table.columns]
        # create a connection
        with engine.connect() as connection:
            print(connection)
            # select the table for the specific year
            query = select(table).where(text("tracks.name LIKE '%Tweezer%'")).order_by(table.c.length_sec.desc())

            result = connection.execute(query)
            print(query)
            # print the results
            out_list = []
            for row in result:
                out_dict = {k: v for k, v in zip(columns, row)}
                out_list.append(out_dict)
            return out_list
