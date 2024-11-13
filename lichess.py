#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import sqlite3
from datetime import date
from typing import Dict

DATABASE_NAME = 'chess_rating.db'
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
    ratings = ('Bullet', 'Blitz', 'Rapid')

    soup = BeautifulSoup(source, 'lxml')

    # Find all 'a' tags with titles that include the game types
    links = soup.find_all('a', title=True)
    for link in links:
        if link.span.h3.text in ratings:
            try:
                ratio = link.span.rating.strong.text.replace('?', "")
                ratio = int(ratio) if ratio else None
                name[f'{link.span.h3.text}'] = f'{ratio}'
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


for player in PLAYERS:
    url = f'https://lichess.org/@/{player}'
    response = requests.get(url)
    if response.status_code == 200:
        name_data = get_rating(response.text, player)
        insert_rating(name_data)
