from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
import re
import json
from typing import Any, Optional, List
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Date, DateTime, ForeignKey, Index, \
    select, \
    inspect, Boolean, update, func, distinct, desc
from sqlalchemy.sql import text, delete
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
    last_played: Optional[datetime]
    times_played: int
    folder_path: str

    @staticmethod
    def from_db(row: tuple) -> Show:
        show_dict = {k: v for k, v in zip(Show.model_fields.keys(), row)}
        show = Show(**show_dict)
        return show

    def __repr__(self):
        played = f"- Played : {self.times_played}" if self.times_played > 0 else ""
        return f"Phish {self.date.strftime('%Y-%m-%d')} {self.venue.title()} {played}"

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

    def backup_last_played(self):
        all_played = self.all_played_show_tracks()
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('played_backup.json')
        backup_list = [
            (show.date.strftime('%Y-%m-%d'), show.last_played.strftime('%Y-%m-%d %H:%M:%S'), show.times_played) for show
            in all_played]
        with open(backup_json, 'w') as file:
            json.dump(backup_list, file)
        print(f"Wrote Special Backup to {backup_json}")

    def restore_last_played(self):
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('played_backup.json')
        if not backup_json.exists():
            raise FileNotFoundError("'special_backup.json' is not found")
        else:
            with open(backup_json, 'r') as file:
                backup_list = json.load(file)
            for show_id, date_time, times_played in backup_list:
                self.update_played_show(show_id, date_time, times_played)

    def backup_track_special(self):
        """ Backs up Special Tracks Booleans """
        special_tracks = self.all_special_show_tracks()
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('special_backup.json')
        # Convert list[Tracks] to list[dict]
        backup_list = [(show.date.strftime('%Y-%m-%d'), track.name) for show, track in special_tracks]
        with open(backup_json, 'w') as file:
            json.dump(backup_list, file)
        print(f"Wrote Special Backup to {backup_json}")

    def restore_track_special(self):
        """ Restores Special Track Booleans """
        backup_folder = Path(self.config.backups_folder)
        backup_json = backup_folder / Path('special_backup.json')
        if not backup_json.exists():
            raise FileNotFoundError("'special_backup.json' is not found")
        else:
            with open(backup_json, 'r') as file:
                backup_list = json.load(file)
            special_tracks = [self.track_by_date_name(show_date, name, exact=True)[1] for show_date, name in
                              backup_list]
            for track in special_tracks:
                self.update_special_track(track)

    def backup_show_special(self):
        raise NotImplementedError

    def restore_show_special(self):
        raise NotImplementedError

    def create(self):
        """ Creates a SQLite Database with the required structure"""
        # define 'shows' table
        self.shows = Table(
            'shows', self.meta,
            Column('show_id', Integer, primary_key=True),
            Column('date', Date),
            Column('venue', String),
            Column('last_played', DateTime, nullable=True),
            Column('times_played', Integer, default=0),
            Column('folder_path', String),
            Column('special', Boolean, default=False),
            # extend_existing=True  # Set this parameter to True
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
            Column('file_path', String),
            # extend_existing=True  # Set this parameter to True
        )

        # create indexes
        Index('ix_shows_date', self.shows.c.date)
        Index('ix_shows_venue', self.shows.c.venue)
        Index('ix_shows_folder_path', self.shows.c.folder_path)
        Index('ix_tracks_name', self.tracks.c.name)
        Index('ix_tracks_file_path', self.tracks.c.file_path)
        # create all tables
        self.meta.create_all(self.engine)
        self.meta.reflect(self.engine)

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
                    track_number = self.k_out_of_n_fix(track_number) if isinstance(track_number,
                                                                                   str) and "/" in track_number else track_number
                    disc_number = audio.get('discnumber')
                    disc_number = disc_number[0] if disc_number else disc_default
                    disc_number = self.k_out_of_n_fix(disc_number) if isinstance(disc_number,
                                                                                 str) and "/" in disc_number else disc_number
                elif file.suffix.lower() in ['.mp3']:
                    audio = MP3(file)
                    track_length_sec = int(audio.info.length)
                    track_name = self.clean_names(audio.tags['TIT2'][0])
                    track_number = audio.tags['TRCK'][0]
                    track_number = self.k_out_of_n_fix(track_number) if isinstance(track_number,
                                                                                   str) and "/" in track_number else track_number
                    disc_number = audio.get('TPOS')
                    disc_number = disc_number[0] if disc_number else disc_default
                    disc_number = self.k_out_of_n_fix(disc_number) if isinstance(disc_number,
                                                                                 str) and "/" in disc_number else disc_number
                elif file.suffix.lower() in ['.m4a']:
                    audio = MP4(file)
                    track_length_sec = int(audio.info.length)
                    track_name = self.clean_names(audio.tags['©nam'][0])
                    track_number = audio.tags['trkn'][0][0]
                    track_number = self.k_out_of_n_fix(track_number) if isinstance(track_number,
                                                                                   str) and "/" in track_number else track_number
                    disc_number = audio.get('disk')
                    disc_number = disc_number[0][0] if disc_number else disc_default
                    disc_number = self.k_out_of_n_fix(disc_number) if isinstance(disc_number,
                                                                                 str) and "/" in disc_number else disc_number
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

    @staticmethod
    def k_out_of_n_fix(k_of_n: str):
        """ Splits out K/N such as 01/06 """
        split = k_of_n.split("/")
        if len(split) != 2:
            raise ValueError("Too many /")
        k, _ = split
        return k

    def drop_all(self):
        with self.engine.connect() as connection:
            # Delete all rows from the shows table
            stmt_shows = delete(self.shows)
            connection.execute(stmt_shows)

            # Delete all rows from the tracks table
            stmt_tracks = delete(self.tracks)
            connection.execute(stmt_tracks)

            # Remove all indexes
            Index('ix_shows_date', self.shows.c.date).drop(bind=connection, checkfirst=True)
            Index('ix_shows_venue', self.shows.c.venue).drop(bind=connection, checkfirst=True)
            Index('ix_shows_folder_path', self.shows.c.folder_path).drop(bind=connection, checkfirst=True)
            Index('ix_tracks_name', self.tracks.c.name).drop(bind=connection, checkfirst=True)
            Index('ix_tracks_file_path', self.tracks.c.file_path).drop(bind=connection, checkfirst=True)

            # Commit the transaction
            # self.meta.reflect(connection)
            self.meta.drop_all(connection)
            connection.commit()
            print("Dropping Tables")

    def last_played_shows(self, last_n: int = 1):
        with self.engine.connect() as connection:
            query = select(self.shows.c.last_played).order_by(desc(self.shows.c.last_played)).limit(last_n)
            last_played_date = connection.execute(query)
            last_played_date = [last_date[0].strftime('%Y-%m-%d') for last_date in last_played_date]
            query = select(self.shows).filter(self.shows.c.last_played.in_(last_played_date))
            results = connection.execute(query)
            return [Show.from_db(row) for row in results]

    def reset_last_played_show_played(self, last_n: int = 1):
        last_played_shows = self.last_played_shows(last_n=last_n)
        last_played_shows = [show.show_id for show in last_played_shows]
        with self.engine.connect() as connection:
            stmt = (update(self.shows)
                    .where(self.show.show_id.in_(last_played_shows))
                    .values(last_played=None,
                            times_played=0))
            connection.execute(stmt)
            connection.commit()

    def reset_played_shows(self, shows: list[Show]):
        """ Resets the times played and last played values in show table """
        show_ids = [show.show_id for show in shows]
        with self.engine.connect() as connection:
            new_last_played = None
            new_times_played = 0
            stmt = (update(self.shows)
                    .where(self.shows.c.show_id.in_(show_ids))
                    .where(self.shows.c.times_played > 0)
                    .values(last_played=new_last_played,
                            times_played=new_times_played))
            connection.execute(stmt)
            connection.commit()

    def update_played_show(self, show_date: str, update_time: str = None, new_times_played: int = None):
        """ Update a Played Show's values """
        if not update_time:
            update_time = datetime.now()
        else:
            update_time = datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S')
        if not new_times_played:
            new_times_played = self.shows.c.times_played + 1
        with self.engine.connect() as connection:
            stmt = (update(self.shows)
                    .where(self.shows.c.date == show_date)
                    .values(last_played=update_time,
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

    def update_special_show(self, show: Show):
        show_id = show.show_id
        raise NotImplementedError

    def delete_shows(self, where_clause: str, confirm: bool = True) -> list[int]:
        """ Delete Shows Based on Arbitrary Where Clause"""
        with self.engine.connect() as connection:
            # First, select the shows based on the where_clause for retrieval.
            selection_query = select(self.shows).where(text(where_clause))
            matching_shows = connection.execute(selection_query)
            shows_to_delete = [Show.from_db(row) for row in matching_shows]
            if not shows_to_delete:
                raise ValueError('No Shows Found')
            to_delete = []
            for show in shows_to_delete:
                if confirm:
                    response = input(f"Delete {show.__repr__()}? - [y/n]")
                    if response.lower().strip() == 'n':
                        print("Not Deleted")
                        continue
                    elif response.lower().strip() == 'y':
                        to_delete.append(show.show_id)
                    else:
                        raise ValueError("response must be in {y,n}")
            if to_delete:
                deletion_query = delete(self.shows).where(self.shows.c.show_id.in_(to_delete))
                connection.execute(deletion_query)
                connection.commit()
                return to_delete
            else:
                raise ValueError('Nothing Deleted')

    def check_duplicates_dates(self):
        with self.engine.connect() as connection:
            query = select(self.shows.c.date).group_by(self.shows.c.date).having(func.count(self.shows.c.date) > 1)
            result = connection.execute(query)
            return [show.date.strftime('%Y-%m-%d') for show in result]

    def total_shows(self) -> int:
        """ Returns a count of the total number of shows """
        with self.engine.connect() as connection:
            query = text("SELECT COUNT(show_id) FROM shows")
            result = connection.execute(query)
            total_shows = list(result)[0][0]
            return total_shows

    def random_shows(self, k: int = 1, exclude_played: bool = True, exclude_show_ids: list = None):
        if exclude_show_ids is None:
            exclude_show_ids = []
        with (self.engine.connect() as connection):
            query = select(self.shows)
            if exclude_show_ids:
                query = query.where(~self.shows.c.show_id.in_(exclude_show_ids))
            if exclude_played:
                query = query.where(self.shows.c.times_played == 0)
            query = query.order_by(func.random()).limit(k)
            results = connection.execute(query)
            return [Show.from_db(row) for row in results]

    def random_tracks(self, k: int = 1):
        with self.engine.connect() as connection:
            query = select(self.tracks).order_by(func.random()).limit(k)
            results = connection.execute(query)
            return [Track.from_db(row) for row in results]

    def all_shows(self) -> list[Show]:
        """ Returns a list of all shows """
        with self.engine.connect() as connection:
            query = select(self.shows).order_by(self.shows.c.date)
            results = connection.execute(query)
            return [Show.from_db(row) for row in results]

    def all_tracks(self) -> list[Track]:
        """ Returns a list of all tracks """
        with self.engine.connect() as connection:
            query = select(self.tracks)
            results = connection.execute(query)
            return [Track.from_db(row) for row in results]

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

    def track_from_id(self, track_id: int) -> Track:
        """ Return a Track given a track_id """
        with self.engine.connect() as connection:
            query = select(self.tracks).where(self.tracks.c.track_id == track_id)
            results = connection.execute(query)
            results = [Track.from_db(row) for row in results]
            if len(results) > 1:
                raise IndexError('Multiple Shows Found')
            elif not results:
                raise ValueError('No Show Found')
            return results[0]

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

    def tracks_by_name(self, track_name: str, exact: bool = False) -> list[Track]:
        with self.engine.connect() as connection:
            if exact:
                query = select(self.tracks).where(self.tracks.c.name == track_name.lower())
            else:
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
            elif not results:
                raise ValueError('No Show Found')
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
            elif not results:
                raise ValueError('No Show Found')
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

    def all_special_shows(self):
        raise NotImplementedError

    def all_played_show_tracks(self) -> list[Show]:
        with self.engine.connect() as connection:
            query = (select(self.shows)
                     .where(text("shows.last_played > 0"))
                     )
            results = connection.execute(query)
            return [Show.from_db(row) for row in results]


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
# pd.drop_all()
# # pd.backup_special()
# pd.restore_special()
# pd.all_show_dates()
# pd.all_track_names()
# pd.tracks_by_name('Ghost')
# print(conf.is_configured())
# pd.last_played_shows(1)
# pd.restore_last_played()
# print(pd.total_shows())

# Delete Path
# conf = Configuration.from_json()
# conf.delete_configuration_folder()
