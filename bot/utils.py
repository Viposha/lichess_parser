from bs4 import BeautifulSoup
from typing import Dict
import sqlite3
from datetime import date

today = date.today()
DATABASE_NAME = '/root/projects/lichess_parser/chess_rating.db'


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


def get_all_player_ratings():
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    # Select all Blitz ratings for the given name
    cursor.execute("SELECT Name, Bullet, Blitz, Rapid, Date FROM rating WHERE Date = ?", (today,))
    results = cursor.fetchall()  # Fetch all matching results

    connection.close()

    # Return results as a list of dictionaries for better readability
    players = [
        {
            'Name': row[0],
            'Bullet': row[1],
            'Blitz': row[2],
            'Rapid': row[3],
            'Date': row[4]
        }
        for row in results
    ]
    return players


# Function to query database for selected player name and rating type
def get_rating_by_name_and_type(player_name, rating_type):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # SQL query to select Date and the selected rating type for the given player name
    cursor.execute(f"SELECT Date, {rating_type} FROM rating WHERE Name = ?", (player_name,))
    rows = cursor.fetchall()
    conn.close()
    return rows
