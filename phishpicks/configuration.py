from __future__ import annotations
import os.path
from os import PathLike
from pathlib import Path
from typing import Union
from pydantic import BaseModel
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Date, ForeignKey, Index
from sqlalchemy.orm import sessionmaker


class Configuration(BaseModel):
    config_folder: Union[PathLike, Path, str] = ".phishpicks"
    phish_folder: Union[PathLike, Path, str] = "Z:\Music\Phish"
    phish_db: str = "phish.db"

    def is_configured(self) -> bool:
        """ Checks if configuration exists and is complete """
        # Config Folder Exists?
        # DB Exists?
        # DB Tables Have Content?
        # Phish Folder Exists and has Folders?
        raise NotImplementedError

    def is_configuration_folder(self) -> bool:
        user_folder = Path(os.path.expanduser("~"))
        config_folder = user_folder / Path(self.config_folder)
        return config_folder.exists()

    def is_phish_folder(self) -> bool:
        return Path(self.phish_folder).exists()

    def is_db(self) -> bool:
        user_folder = Path(os.path.expanduser("~"))
        db_location = user_folder / Path(self.config_folder) / Path(self.phish_db)
        return db_location.exists()

    def create_configuration_folder(self):
        user_folder = Path(os.path.expanduser("~"))
        config_folder = user_folder / Path(self.config_folder)
        config_folder.mkdir(parents=False, exist_ok=True)

    def create_db(self):
        self.create_configuration_folder()
        user_folder = Path(os.path.expanduser("~"))
        db_location = user_folder / Path(self.config_folder) / Path(self.phish_db)
        print(db_location)
        engine = create_engine(f'sqlite:///{db_location}', echo=True)
        meta = MetaData()

        # define 'shows' table
        shows = Table(
            'shows', meta,
            Column('show_id', Integer, primary_key=True),
            Column('show_date', Date),
            Column('show_location', String),
            Column('folder_path', String)
        )

        # define 'tracks' table
        tracks = Table(
            'tracks', meta,
            Column('track_id', Integer, primary_key=True),
            Column('show_id', Integer, ForeignKey('shows.show_id')),
            Column('track_number', Integer),
            Column('track_name', String),
            Column('track_filetype', String),
            Column('track_length_sec', Integer),
            Column('file_path', String)
        )

        # create indexes
        Index('ix_shows_show_date', shows.c.show_date)
        Index('ix_shows_show_location', shows.c.show_location)
        Index('ix_shows_folder_path', shows.c.folder_path)
        Index('ix_tracks_track_name', tracks.c.track_name)
        Index('ix_tracks_file_path', tracks.c.file_path)
        # create all tables
        meta.create_all(engine)

        # start session
        session = sessionmaker(bind=engine)
        session.close_all()

    def populate_db(self, shows_data, tracks_data):
        # Create engine and start session
        user_folder = Path(os.path.expanduser("~"))
        db_location = user_folder / Path(self.config_folder) / Path(self.phish_db)
        print(db_location)
        engine = create_engine(f'sqlite:///{db_location}', echo=True)
        Session = sessionmaker(bind=engine)

        # Insert shows and tracks
        with Session() as session:
            for show in shows_data:
                show_obj = shows(**show)
                session.add(show_obj)

            for track in tracks_data:
                track_obj = tracks(**track)
                session.add(track_obj)

            session.commit()

        # Close session
        session.close()
