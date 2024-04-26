import pytest
from datetime import date
from phishpicks import Show


def test_show_from_db():
    db_row = (725, date(2024, 4, 21), 'Sphere Las Vegas, NV', None, 0, 'Phish 2024-04-21 Sphere Las Vegas, NV')
    show = Show.from_db(db_row)
    out_dict = {'show_id': 725,
                'date': date(2024, 4, 21),
                'venue': 'Sphere Las Vegas, NV',
                'last_played': None,
                'times_played': 0,
                'folder_path': 'Phish 2024-04-21 Sphere Las Vegas, NV'}
    assert show.__dict__ == out_dict
