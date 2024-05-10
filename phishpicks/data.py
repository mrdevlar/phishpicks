from __future__ import annotations
from datetime import date
from pathlib import Path
import re
import json
from typing import Any, Optional
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Date, ForeignKey, Index, select, \
    inspect, Boolean, update, func, distinct
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
from phishpicks.configuration import Configuration
from pydantic import BaseModel
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4


# @TODO: Backup all times played in show, all tracks special

class Track(BaseModel):
    track_id: int
    show_id: int
    disc_number: int
    track_number: int
    name: str
    filetype: str
    length_sec: int
    special: bool
    file_path: str

    @staticmethod
    def from_db(row: tuple) -> Track:
        track_dict = {k: v for k, v in zip(Track.model_fields.keys(), row)}
        track = Track(**track_dict)
        return track

    def __repr__(self):
        special = "Special" if self.special else ""
        return f"{self.disc_number}{self.track_number:02d} {self.name.title()} {self.length_sec} {special}"

    def __lt__(self, other):
        return self.name < other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def to_show(self, phish_data: Optional[PhishData] = None):
        if not phish_data:
            conf = Configuration()
            phish_data = PhishData(config=conf)
        return phish_data.show_from_id(self.show_id)


class Show(BaseModel):
    show_id: int
    date: date
    venue: str
    last_played: Optional[date]
    times_played: int
    folder_path: str

    @staticmethod
    def from_db(row: tuple) -> Show:
        show_dict = {k: v for k, v in zip(Show.model_fields.keys(), row)}
        show = Show(**show_dict)
        return show

    def __repr__(self):
        return f"Phish {self.date.strftime('%Y-%m-%d')} {self.venue.title()}"

    def __lt__(self, other):
        return self.date < other.date

    def __eq__(self, other: object) -> bool:
        return self.date == other.date

    def __hash__(self) -> int:
        return hash(self.date)


class PhishData(BaseModel):
    config: Configuration
    db_location: Path = None
    engine: Any = None
    meta: Any = None
    shows: Any = None
    tracks: Any = None
    inspector: Any = None

    def model_post_init(self, __context: Any):
        self.db_location = self.config.config_folder / Path(self.config.phish_db)
        self.engine = create_engine(f'sqlite:///{self.db_location}', echo=False)
        self.inspector = inspect(self.engine)
        self.meta = MetaData()

        if self.inspector.has_table('shows'):
            self.shows = Table('shows', self.meta, autoload_with=self.engine)
        else:
            print("No 'shows' table found")
            self.shows = None
        if self.inspector.has_table('tracks'):
            self.tracks = Table('tracks', self.meta, autoload_with=self.engine)
        else:
            print("No 'tracks' table found")
            self.shows = None

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

    def backup_special(self):
        """ Backs up Special Tracks Booleans """
        special_tracks = self.all_special_show_tracks()
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('special_backup.json')
        # Convert list[Tracks] to list[dict]
        backup_list = [(show.date.strftime('%Y-%m-%d'), track.name) for show, track in special_tracks]
        with open(backup_json, 'w') as file:
            json.dump(backup_list, file)
        print(f"Wrote Special Backup to {backup_json}")

    def restore_special(self):
        """ Restores Special Track Booleans """
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('special_backup.json')
        if not backup_json.exists():
            raise FileNotFoundError("'special_backup.json' is not found")
        else:
            with open(backup_json, 'r') as file:
                backup_list = json.load(file)
            special_tracks = [self.track_by_date_name(date, name, exact=True)[1] for date, name in backup_list]
            for track in special_tracks:
                self.update_special_track(track)

    def create(self):
        """ Creates a SQLite Database with the required structure"""
        self.config.create_configuration_folder()

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
            Column('disc_number', Integer),
            Column('track_number', Integer),
            Column('name', String),
            Column('filetype', String),
            Column('length_sec', Integer),
            Column('special', Boolean, default=False),
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
        for folder in Path(self.config.phish_folder).glob(self.config.show_glob):
            # WindowsPath('Z:/Music/Phish/Phish 1989-08-26 Townshend, VT (LivePhish 09) [FLAC]')
            date_re = r'\d\d\d\d-\d\d\-\d\d'
            show_date = re.findall(date_re, folder.name)[0]
            venue_re = self.config.venue_regex
            show_venue = re.findall(venue_re, folder.name)
            show_venue = show_venue[0].strip().lower() if show_venue else 'None'
            folder_path = folder.name

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
                disc_default = '0'
                # print(file)
                if file.suffix.lower() in ['.flac']:
                    audio = FLAC(file)
                    track_length_sec = int(audio.info.length)
                    track_name = self.clean_names(audio.get('title')[0])
                    track_number = audio.get('tracknumber')[0]
                    disc_number = audio.get('discnumber')
                    disc_number = disc_number[0] if disc_number else disc_default
                    # print(file)
                elif file.suffix.lower() in ['.mp3']:
                    audio = MP3(file)
                    track_length_sec = int(audio.info.length)
                    track_name = self.clean_names(audio.tags['TIT2'][0])
                    track_number = audio.tags['TRCK'][0]
                    disc_number = audio.get('TPOS')
                    disc_number = disc_number[0] if disc_number else disc_default
                    # print(file)
                elif file.suffix.lower() in ['.m4a']:
                    audio = MP4(file)
                    track_length_sec = int(audio.info.length)
                    track_name = self.clean_names(audio.tags['©nam'][0])
                    track_number = audio.tags['trkn'][0][0]
                    disc_number = audio.get('disk')
                    disc_number = disc_number[0][0] if disc_number else disc_default
                    # print(file)
                else:
                    print(f"Unsupported File: {file}")
                    unsupported.append(str(file))
                    continue
                    # raise TypeError("Unsupported file format")

                track_insert = self.tracks.insert().values(
                    show_id=show_id,
                    disc_number=disc_number,
                    track_number=track_number,
                    name=track_name.lower(),
                    filetype=track_filetype,
                    length_sec=track_length_sec,
                    file_path=file_path,
                )
                session.execute(track_insert)
                session.commit()

        # Close session
        session.close()

    def reset_played_shows(self):
        """ Resets the times played and last played values in show table """
        with self.engine.connect() as connection:
            new_last_played = None
            new_times_played = 0
            stmt = (update(self.shows)
                    .where(self.shows.c.times_played > 0)
                    .values(last_played=new_last_played,
                            times_played=new_times_played))
            connection.execute(stmt)
            connection.commit()

    def update_played_show(self, show: Show):
        """ Update a Played Show's values """
        show_id = show.show_id
        with self.engine.connect() as connection:
            new_last_played = date.today()
            new_times_played = self.shows.c.times_played + 1
            stmt = (update(self.shows)
                    .where(self.shows.c.show_id == show_id)
                    .values(last_played=new_last_played,
                            times_played=new_times_played))
            connection.execute(stmt)
            connection.commit()

    def update_special_track(self, track: Track):
        track_id = track.track_id
        with self.engine.connect() as connection:
            stmt = (update(self.tracks)
                    .where(self.tracks.c.track_id == track_id)
                    .values(special=True))
            connection.execute(stmt)
            connection.commit()
        print(f"Special Add: {track}")

    def total_shows(self) -> int:
        """ Returns a count of the total number of shows """
        with self.engine.connect() as connection:
            query = text("SELECT COUNT(show_id) FROM shows")
            result = connection.execute(query)
            total_shows = list(result)[0][0]
            return total_shows

    def all_shows(self) -> list[Show]:
        """ Returns a list of all shows """
        with self.engine.connect() as connection:
            query = select(self.shows).order_by(self.shows.c.date)
            results = connection.execute(query)
            return [Show.from_db(row) for row in results]

    def all_show_dates(self) -> list:
        """ All show dates to use with autocompleter """
        with self.engine.connect() as connection:
            query = select(distinct(self.shows.c.date)).order_by(self.shows.c.date)
            results = connection.execute(query)
            results = [row[0].strftime("%Y-%m-%d") for row in results]
            return results

    def all_track_names(self) -> list:
        """ All track names for use with autocompleter """
        with self.engine.connect() as connection:
            query = select(distinct(self.tracks.c.name)).order_by(self.tracks.c.name)
            results = connection.execute(query)
            results = [self.clean_names(row[0]) for row in results]
            return results

    @staticmethod
    def clean_names(name: str) -> str:
        name = name.replace("->", "")
        name = name.replace(">", "")
        name = name.replace("_", " ")
        name = name.strip()
        name = name.lower()
        return name

    def query_shows(self, where_clause: str) -> list[Show]:
        """ Execute an arbitrary where on shows """
        with self.engine.connect() as connection:
            query = select(self.shows).where(text(where_clause))
            results = connection.execute(query)
            return [Show.from_db(row) for row in results]

    def query_tracks(self, where_clause: str) -> list[Track]:
        """ Execute an arbitrary where on shows """
        with self.engine.connect() as connection:
            query = select(self.tracks).where(text(where_clause))
            results = connection.execute(query)
            return [Track.from_db(row) for row in results]

    def track_by_date_name(self, show_date: str, track_name: str, exact: bool = False) -> tuple[Show, Track]:
        """
        Select a Unique Track and Show
        This should only return one value, as the date track combo is unique.

        Args:
            show_date: Show date in 'YYYY-MM-DD' format
            track_name: Track name wildcard, LIKE
            exact: Exact string match?

        Returns:
            dict with {'show': Show, 'track': Track}
        """
        with self.engine.connect() as connection:
            if exact:
                query = (select(self.shows, self.tracks)
                         .where(self.shows.c.date == show_date)
                         .where(self.tracks.c.name == track_name.lower())
                         .select_from(self.shows.join(self.tracks, self.shows.c.show_id == self.tracks.c.show_id))
                         )
            else:
                query = (select(self.shows, self.tracks)
                         .where(self.shows.c.date == show_date)
                         .where(self.tracks.c.name.like('%' + track_name.lower() + '%'))
                         .select_from(self.shows.join(self.tracks, self.shows.c.show_id == self.tracks.c.show_id))
                         )
            results = connection.execute(query)
            results = [(Show.from_db(row[:6]), Track.from_db(row[6:])) for row in results]
            if len(results) > 1:
                print(results)
                raise IndexError('Multiple Tracks Found')
            elif not results:
                raise IndexError('No Track Found')
            return results[0]

    def tracks_by_name(self, track_name: str) -> list[Track]:
        with self.engine.connect() as connection:
            query = select(self.tracks).where(self.tracks.c.name.like('%' + track_name.lower() + '%'))
            results = connection.execute(query)
            return [Track.from_db(row) for row in results]

    def show_from_id(self, show_id: int) -> Show:
        """ Return a Show given a show_id """
        with self.engine.connect() as connection:
            query = select(self.shows).where(self.shows.c.show_id == show_id)
            results = connection.execute(query)
            results = [Show.from_db(row) for row in results]
            if len(results) > 1:
                raise IndexError('Multiple Shows Found')
            return results[0]

    def show_by_date(self, show_date: str):
        date_regex = r'\d{4}-\d{2}-\d{2}'
        date_match = re.search(date_regex, show_date)
        if not date_match:
            raise TypeError('show_date must be in YYYY-MM-DD format')
        with self.engine.connect() as connection:
            query = select(self.shows).where(self.shows.c.date == show_date)
            results = connection.execute(query)
            results = [Show.from_db(row) for row in results]
            if len(results) > 1:
                raise IndexError('Multiple Shows Found')
            return results[0]

    def shows_from_tracks(self, tracks: list[Track]) -> list[Show]:
        show_ids = [track.show_id for track in tracks]
        with self.engine.connect() as connection:
            query = select(self.shows).where(self.shows.c.show_id.in_(show_ids))
            results = connection.execute(query)
            return [Show.from_db(row) for row in results]

    def tracks_from_date(self, show_date: str) -> list[Track]:
        with self.engine.connect() as connection:
            query = (select(self.tracks)
                     .where(self.shows.c.date == show_date)
                     .select_from(self.shows.join(self.tracks, self.shows.c.show_id == self.tracks.c.show_id))
                     )
            results = connection.execute(query)
            return [Track.from_db(row) for row in results]

    def tracks_from_shows(self, shows: list[Show]) -> list[Track]:
        show_ids = [show.show_id for show in shows]
        with self.engine.connect() as connection:
            query = select(self.tracks).where(self.tracks.c.show_id.in_(show_ids))
            results = connection.execute(query)
            return [Track.from_db(row) for row in results]

    def all_special_tracks(self) -> list[Track]:
        with self.engine.connect() as connection:
            query = select(self.tracks).where(text("tracks.special = True"))
            results = connection.execute(query)
            return [Track.from_db(row) for row in results]

    def all_special_show_tracks(self) -> list[tuple[Show, Track]]:
        with self.engine.connect() as connection:
            query = (select(self.shows, self.tracks)
                     .where(text("tracks.special = True"))
                     .select_from(self.shows.join(self.tracks, self.shows.c.show_id == self.tracks.c.show_id))
                     )
            results = connection.execute(query)
            results = [(Show.from_db(row[:6]), Track.from_db(row[6:])) for row in results]
            return results


class QueryLexer(BaseModel):
    expression: str
    keywords: Any = None
    identifiers: Any = None
    operators: Any = None
    literals: Any = None

    def parse(self):
        print(self.expression)

    def parse_date(self):
        # /d/d/d/d-
        # Must be in show or track state
        raise NotImplementedError




# Not configured Path
# conf = Configuration()
# conf.create_configuration_folder()
# conf.save_to_json()
# pd = PhishData(config=conf)
# print(pd)
# pd.create()
# pd.populate()
# check_folders = conf.total_phish_folders() == pd.total_shows()
# print(check_folders)

# # # Already Configured Path
# conf = Configuration.from_json()
# pd = PhishData(config=conf)
# # pd.backup_special()
# pd.restore_special()
# pd.all_show_dates()
# pd.all_track_names()
# pd.tracks_by_name('Ghost')
# print(conf.is_configured())
# print(pd.total_shows())

# Delete Path
# conf = Configuration.from_json()
# conf.delete_configuration_folder()
