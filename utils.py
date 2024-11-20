from bs4 import BeautifulSoup
from typing import Dict
import sqlite3
from datetime import date

DATABASE_NAME = '/root/projects/lichess_parser/chess_rating.db'
SQL_CREATE_TABLE = """CREATE TABLE IF NOT EXISTS rating (
                    Name text,
                    Bullet integer,
                    Blitz integer,
                    Rapid integer,
                    Date text
                    )"""


PLAYERS = ('Evgeniy1989', 'Pyrog_Ivan', 'Viposha')


def initialize_db():
    """Initialize the database and create the table if it doesn't exist."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(SQL_CREATE_TABLE)
        conn.commit()
        c.close()


def get_rating(source, nick:str) -> Dict:
    """Parse lichess.com for 1 player and return data in dict"""
    name = {'nickname': nick, 'Bullet': None, 'Blitz': None, 'Rapid': None}
    soup = BeautifulSoup(source, 'lxml')
    article = soup.find_all('span')
    for art in article:
        if art.span:
            try:
                ratio = art.rating.strong.text.replace('?', "")
                ratio = int(ratio) if ratio else None
                name[f'{art.h3.text}'] = f'{ratio}'
            except Exception as e:
                print(e)
    return name


def insert_rating(player_dict: Dict):
    """Insert collected data to DB"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO rating VALUES (:Name, :Bullet, :Blitz, :Rapid, :Date)',
       {
           'Name': player_dict['nickname'],
           'Bullet': player_dict['Bullet'],
           'Blitz': player_dict['Blitz'],
           'Rapid': player_dict['Rapid'],
           'Date': date.today()
                    }
                    )
        conn.commit()
        c.close()
