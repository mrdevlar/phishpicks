from __future__ import annotations
from datetime import date
from pathlib import Path
import re
from typing import Any

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Date, ForeignKey, Index, select
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
from phishpicks.configuration import Configuration
from pydantic import BaseModel

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4


class PhishData(BaseModel):
    config: Configuration
    db_location: Path = None
    engine: Any = None
    meta: Any = None
    shows: Any = None
    tracks: Any = None

    def model_post_init(self, __context: Any):
        self.db_location = self.config.config_folder / Path(self.config.phish_db)
        self.engine = create_engine(f'sqlite:///{self.db_location}', echo=True)
        self.meta = MetaData()
        self.shows = Table('shows', self.meta, autoload_with=self.engine)
        self.tracks = Table('tracks', self.meta, autoload_with=self.engine)

    def status(self):
        """ Prints the status of the Database """
        raise NotImplementedError

    def exists(self) -> bool:
        """ Checks if Database exists """
        if self.config.is_configuration_folder():
            if self.config.is_db():
                return True
            else:
                return False
        else:
            raise FileNotFoundError(f"Configuration Folder {self.config.config_folder} does not exist")

    def verify(self):
        """ Verifies that Database has correct number of shows"""
        raise NotImplementedError

    def create(self):
        """ Creates a SQLite Database with the required structure"""
        self.conf.create_configuration_folder()

        # define 'shows' table
        self.shows = Table(
            'shows', self.meta,
            Column('show_id', Integer, primary_key=True),
            Column('date', Date),
            Column('venue', String),
            Column('last_played', Date, nullable=True),
            Column('times_played', Integer, default=0),
            Column('folder_path', String)
        )

        # define 'tracks' table
        self.tracks = Table(
            'tracks', self.meta,
            Column('track_id', Integer, primary_key=True),
            Column('show_id', Integer, ForeignKey('shows.show_id')),
            Column('track_number', Integer),
            Column('name', String),
            Column('filetype', String),
            Column('length_sec', Integer),
            Column('file_path', String)
        )

        # create indexes
        Index('ix_shows_date', self.shows.c.date)
        Index('ix_shows_venue', self.shows.c.venue)
        Index('ix_shows_folder_path', self.shows.c.folder_path)
        Index('ix_tracks_name', self.tracks.c.name)
        Index('ix_tracks_file_path', self.tracks.c.file_path)
        # create all tables
        self.meta.create_all(self.engine)

    def populate(self):
        """ Populates the Database with show and track information"""
        # Create engine and start session

        Session = sessionmaker(bind=self.engine)
        session = Session()

        # Traverse folders and add show data to the shows table
        for folder in Path(self.phish_folder).glob("Phish [0-9]*"):
            # WindowsPath('Z:/Music/Phish/Phish 1989-08-26 Townshend, VT (LivePhish 09) [FLAC]')
            show_date = folder.name[6:16]
            venue_re = r'Phish \d\d\d\d-\d\d-\d\d (.*?.*)'
            show_venue = re.findall(venue_re, folder.name)
            show_venue = show_venue[0].strip() if show_venue else 'None'
            folder_path = folder.stem

            show_insert = self.shows.insert().values(date=date.fromisoformat(show_date),
                                                     venue=show_venue,
                                                     folder_path=folder_path)
            session.execute(show_insert)
            session.commit()

            show_id = session.query(self.shows.c.show_id).filter(self.shows.c.folder_path == folder_path).scalar()

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

                track_insert = self.tracks.insert().values(
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

    def total_shows(self) -> int:
        with self.engine.connect() as connection:
            query = text("SELECT COUNT(show_id) FROM shows")
            result = connection.execute(query)
            total_shows = list(result)[0][0]
            return total_shows

    def query(self) -> list:
        columns = [column.name for column in self.tracks.columns]
        # create a connection
        with self.engine.connect() as connection:
            print(connection)
            # select the table for the specific year
            query = select(self.tracks).where(text("tracks.name LIKE '%Tweezer%'")).order_by(
                self.tracks.c.length_sec.desc())

            result = connection.execute(query)
            print(query)
            # print the results
            out_list = []
            for row in result:
                out_dict = {k: v for k, v in zip(columns, row)}
                out_list.append(out_dict)
            return out_list


conf = Configuration.from_json()
pd = PhishData(config=conf)
print(pd.total_shows())
print("ham")
