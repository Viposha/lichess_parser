import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import sqlite3
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
from typing import Dict
import requests
import matplotlib.pyplot as plt
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
import matplotlib.dates as mdates
import json

today = date.today()
PLAYERS = ('Evgeniy1989', 'Pyrog_Ivan', 'Viposha')
RATING_TYPES = ('Bullet', 'Blitz', 'Rapid')
DATABASE_NAME = '/root/chess_rating.db'
STATUS_MAP = {
    "mate": "by checkmate",
    "resign": "by resignation",
    "outoftime": "on time",
    "draw": "drawn",
    "stalemate": "by stalemate",
    "aborted": "aborted",
    "timeout": "on time",
    "noStart": "not started",
    "cheat": "game ended due to cheat detection",
    "variantEnd": "variant end",
    "unknownFinish": "finished (reason unknown)"
}

# Dictionary to store the selected player names by user_id
user_selected_players = {}

tok = os.getenv("CHESSTOKEN")
bot = Bot(token=tok)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


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
    connection = sqlite3.connect('/root/chess_rating.db')
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
    conn = sqlite3.connect('/root/chess_rating.db')
    cursor = conn.cursor()
    # SQL query to select Date and the selected rating type for the given player name
    cursor.execute(f"SELECT Date, {rating_type} FROM rating WHERE Name = ?", (player_name,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# Command handler for /graph to ask user to choose a player name
@dp.message(Command("graph"))
async def graph_command_handler(message: Message):
    # Create inline keyboard with player names
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=player, callback_data=f"select_player_{player}")] for player in
                         PLAYERS]
    )
    await message.answer("Please choose your player name:", reply_markup=keyboard)


# Callback handler for player name selection, proceeds to select rating type
@dp.callback_query(lambda callback_query: callback_query.data.startswith("select_player_"))
async def handle_player_selection(callback_query: CallbackQuery):
    # Extract the selected player name from the callback data
    player_name = callback_query.data.split("select_player_")[1]

    # Store the chosen player name in the user_selected_players dictionary
    user_selected_players[callback_query.from_user.id] = player_name

    # Ask user to select a rating type
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=rating, callback_data=f"select_rating_{rating}")] for rating in
                         RATING_TYPES]
    )
    await callback_query.message.answer(f"Player '{player_name}' selected. Now, please choose the rating type:",
                                        reply_markup=keyboard)
    await callback_query.answer()


# Callback handler for rating type selection and database query execution
@dp.callback_query(lambda callback_query: callback_query.data.startswith("select_rating_"))
async def handle_rating_selection(callback_query: CallbackQuery):
    # Extract the rating type from the callback data
    rating_type = callback_query.data.split("select_rating_")[1]

    # Retrieve the selected player name for this user
    player_name = user_selected_players.get(callback_query.from_user.id)

    # If the player name is not found, send an error message
    if not player_name:
        await callback_query.message.answer("Error: Player name not found. Please start over by using /graph.")
        return

    # Query the database for the selected name and rating type
    rows = get_rating_by_name_and_type(player_name, rating_type)

    # Prepare the response message with the query results
    if rows:
        response = f"Results for player '{player_name}' with rating type '{rating_type}':\n"
        response += "\n".join(f"Date: {row[0]}, {rating_type} rating: {row[1]}" for row in rows)
    else:
        response = f"No results found for player '{player_name}' with rating type '{rating_type}'."


    # Filter data to only include the last month's ratings
    one_month_ago = datetime.now() - timedelta(days=30)
    filtered_rows = [row for row in rows if datetime.strptime(row[0], '%Y-%m-%d') >= one_month_ago]

    # Get data from the database
    data = get_rating_by_name_and_type(player_name, rating_type)

    # Prepare data for plotting
    dates = [entry[0] for entry in filtered_rows]
    bullet_ratings = [entry[1] for entry in filtered_rows]
    bullet_ratings = [0 if x == '' or x == 'None' else x for x in bullet_ratings]

    # Generate the plot
    # Convert string dates to datetime objects
    dates = [datetime.strptime(date, '%Y-%m-%d') for date in dates]
    nums = [int(num) for num in bullet_ratings]

    # Create the plot
    plt.plot(dates, nums)

    # Format the date on the x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())

    # Rotate date labels for better readability
    plt.xticks(rotation=45)

    # Add labels and title
    plt.xlabel('Date')
    plt.ylabel('Rating')
    plt.title(f'{rating_type} rating of {player_name}')

    # Save the plot as a file on disk
    file_path = 'bullet_rating.png'
    plt.savefig(file_path)  # Save the figure to a file

    # Send the saved plot as a photo (file)
    input_file = FSInputFile(file_path)  # Use the file path
    await callback_query.message.answer_photo(photo=input_file)
    await callback_query.answer()

    # Cleanup
    plt.close()  # Close the plot to free up memory


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello, chess boys!")


@dp.message(Command("live"))
async def cmd_start(message: types.Message):
    today = date.today()
    result = ""
    for player in PLAYERS:
        url = f'https://lichess.org/@/{player}'
        response = requests.get(url)
        if response.status_code == 200:
            name_data = get_rating(response.text, player)
            result += (
                f"{player}:\n"
                f"  Bullet = {name_data['Bullet']}\n"
                f"  Blitz = {name_data['Blitz']}\n"
                f"  Rapid = {name_data['Rapid']}\n"
                f"  Date = {today}\n\n"
            )
    await message.reply(result)

@dp.message(Command("rating"))
async def cmd_start(message: types.Message):
    players = get_all_player_ratings()

    if players:
        # Format the rating info for each player
        response = ""
        for player in players:
            response += (
                f"Rating of {player['Name']}:\n"
                f"  Bullet = {player['Bullet']}\n"
                f"  Blitz = {player['Blitz']}\n"
                f"  Rapid = {player['Rapid']}\n"
                f"  Date = {player['Date']}\n\n"
            )
    else:
        response = "No player ratings found in the database."

    # Send the response to the user
    await message.reply(response)

# команда /lastgame
@dp.message(Command("last"))
async def lastgame_command_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=player, callback_data=f"last_player_{player}")]
            for player in PLAYERS
        ]
    )
    await message.answer("Оберіть гравця:", reply_markup=keyboard)


# callback: користувач обрав гравця
@dp.callback_query(lambda c: c.data.startswith("last_player_"))
async def handle_lastgame_selection(callback_query: CallbackQuery):
    player_name = callback_query.data.split("last_player_")[1]

    # 1. Fetch last game
    url = f"https://lichess.org/api/games/user/{player_name}?max=1&moves=true"
    res = requests.get(url, headers={"Accept": "application/x-ndjson"})

    game_json = json.loads(res.text.strip().split("\n")[0])

    # 2. Extract players
    players = game_json["players"]
    white = players["white"]
    black = players["black"]

    white_name = white["user"]["name"]
    white_rating = white.get("rating", "N/A")

    black_name = black["user"]["name"]
    black_rating = black.get("rating", "N/A")

    # 3. Extract winner, status, moves
    winner = game_json.get("winner")  # "white" or "black"
    status_code = game_json.get("status", "unknownFinish")
    status_text = STATUS_MAP.get(status_code, status_code)

    moves_str = game_json["moves"]
    num_moves = len(moves_str.split()) // 2
    variant = game_json["variant"]
    speed = game_json["speed"]

    # 4. Build summary
    if winner:
        if winner == "white":
            result = f"{white_name} ({white_rating}) wins vs {black_name} ({black_rating})"
        else:
            result = f"{black_name} ({black_rating}) wins vs {white_name} ({white_rating})"
        summary = f"{result} {status_text} in {num_moves} moves in {variant} game. Time control {speed}"
    else:
        summary = f"Game between {white_name} ({white_rating}) and {black_name} ({black_rating}) ended {status_text} in {num_moves} moves."

    await callback_query.message.answer(summary)
    await callback_query.answer()


if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
