import sqlite3
from sqlite3 import Error
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm

PLAYER_COLUMNS = ["discord_id", "character_name", "jobs", "signup_date", "num_raids", "involuntary_benches"]
PLAYER_COLUMNS_TYPES = ["integer NOT NULL", "text NOT NULL", "text", "text", "integer", "integer"]

EVENT_COLUMNS = ["name", "timestamp", "participant_names", "participant_ids", "is_bench", "jobs", "role_numbers", "creator_id", "message_link", "state"]
EVENT_COLUMNS_TYPES = ["text NOT NULL", "integer NOT NULL", "text", "text", "text", "text",  "text", "integer NOT NULL", "text", "text NOT NULL"]

SERVER_INFO_COLUMNS = ["key", "value"]
SERVER_INFO_COLUMNS_TYPES = ["text", "text"]


def col_str(col_list):
    col_string = ""
    for c in col_list:
        col_string += str(c) + ","
    return col_string[:-1]


def create_table_sql_command(name, cols, col_types):
    sql_table = f"""CREATE TABLE IF NOT EXISTS {name} (\nid integer PRIMARY KEY,\n"""
    for entry, ty in zip(cols, col_types):
        sql_table += entry + " " + ty + ",\n"
    sql_table = sql_table[:-2] + "\n);"
    return sql_table


def initialize_db_with_tables(conn):
    sql_create_player_table_str: str = create_table_sql_command("players", PLAYER_COLUMNS, PLAYER_COLUMNS_TYPES)
    sql_create_events_table_str: str = create_table_sql_command("events", EVENT_COLUMNS, EVENT_COLUMNS_TYPES)
    sql_create_server_table_str: str = create_table_sql_command("server_info", SERVER_INFO_COLUMNS, SERVER_INFO_COLUMNS_TYPES)

    create_table(conn, sql_create_player_table_str)
    create_table(conn, sql_create_events_table_str)
    create_table(conn, sql_create_server_table_str)


def create_connection(db_file: str):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        Path("./database/").mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect("./database/" + str(db_file) + r".db")

    except Error as e:
        print(e)
    # finally:
    #     if conn:
        #         conn.close()
    return conn


def create_table(conn, create_table_sql: str):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def create_player(conn, player: str):
    """
    Create a new player into the player table
    :param conn:
    :param player:
    :return: player id
    """
    player_col_str = col_str(PLAYER_COLUMNS)
    question_str = col_str(["?" for _ in PLAYER_COLUMNS])
    sql = f''' INSERT INTO players({player_col_str})
              VALUES({question_str}) '''
    cur = conn.cursor()
    cur.execute(sql, player)
    conn.commit()
    return cur.lastrowid


def get_player(conn, discord_id, name):
    """Find the player given id and name"""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM players WHERE discord_id=? AND character_name=?", (discord_id, name))
    return cur.fetchall()


def get_player_by_id(conn, discord_id):
    """Find the player given id"""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM players WHERE discord_id=?", (discord_id,))
    return cur.fetchall()


def get_player_by_name(conn, name):
    """Find the player given id"""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM players WHERE character_name=?", (name,))
    return cur.fetchall()


def update_player(conn, field, value, discord_id: int, character_name: str):
    """
    update character_name, jobs, num_raids of a character
    :param conn:
    :param field:
    :return: discord id
    """
    if field in PLAYER_COLUMNS:
        sql = f''' UPDATE players
                   SET {field} = ?
                   WHERE discord_id = ?
                   AND character_name = ?'''
        cur = conn.cursor()
        cur.execute(sql, (value, discord_id, character_name))
        conn.commit()
    else:
        print(f"{field} not in players columns")


def update_jobs(conn, job_list, discord_id, character_name):
    update_player(conn, "jobs", job_list, discord_id, character_name)


def delete_player(conn, id, name):
    """
    Delete a player by discord_id and character_name
    :param conn:  Connection to the SQLite database
    :param id: discord_id of the player
    :param name: character_name of the player
    :return:
    """
    sql = 'DELETE FROM players WHERE discord_id=? AND character_name=?'
    cur = conn.cursor()
    cur.execute(sql, (id, name))
    conn.commit()


def delete_all_players(conn):
    """
    Delete all rows in the players table
    :param conn: Connection to the SQLite database
    :return:
    """
    sql = 'DELETE FROM players'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()


def create_event(conn, event):
    """
    Create a new event into the events table
    :param conn:
    :param event:
    :return: player id
    """
    event_col_str = col_str(EVENT_COLUMNS)
    question_str = col_str(["?" for _ in EVENT_COLUMNS])
    sql = f''' INSERT INTO events({event_col_str})
               VALUES({question_str}) '''
    cur = conn.cursor()
    cur.execute(sql, event)
    conn.commit()
    return cur.lastrowid


def find_events(conn, field, value):
    """
    Find the id of an event by searching for other fields
    :param field: The database field/column that will be searched
    :param value: The value being searched
    """
    cur = conn.cursor()
    if isinstance(value, str):
        # Add wildcard
        value = f"%{value}%"
    cur.execute(f"SELECT * FROM events WHERE {field} LIKE ?", (value,))
    return cur.fetchall()


def get_event(conn, event_id):
    """Find event given id"""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM events WHERE id=?", (event_id,))
    return cur.fetchall()


def get_last_x_events(conn, x: int):
    """Returns the x latest events"""
    sql = ''' SELECT * FROM events
              ORDER BY rowid DESC
              LIMIT ?'''
    cur = conn.cursor()
    cur.execute(sql, (x,))
    conn.commit()
    return cur.fetchall()


def update_event(conn, field, value, event_id):
    """
    update an event
    :param conn:
    :param field:
    """
    if field in EVENT_COLUMNS:
        sql = f''' UPDATE events
                   SET {field} = ?
                   WHERE id = ?'''
        cur = conn.cursor()
        cur.execute(sql, (value, event_id))
        conn.commit()
    else:
        print(f"{field} not in events columns")


def delete_event(conn, event_id):
    """
    Delete an event by id
    :param conn:  Connection to the SQLite database
    :param event_id: id of the event
    :return:
    """
    sql = 'DELETE FROM events WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, (event_id,))
    conn.commit()


def delete_all_events(conn):
    """
    Delete all rows in the events table
    :param conn: Connection to the SQLite database
    :return:
    """
    sql = 'DELETE FROM events'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()


def get_server_info(conn, key):
    """Find server_info given key"""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM server_info WHERE key=?", (key,))
    return cur.fetchall()


def create_server_info(conn, key, value):
    """
    Create a new info into the server_info table
    """
    info_col_str = col_str(SERVER_INFO_COLUMNS)
    question_str = col_str(["?" for _ in SERVER_INFO_COLUMNS])
    sql = f''' INSERT INTO server_info({info_col_str})
               VALUES({question_str}) '''
    cur = conn.cursor()
    cur.execute(sql, (key, value))
    conn.commit()
    return cur.lastrowid


def update_server_info(conn, key, value):
    """
    update an entry of server_info
    """
    sql = f''' UPDATE server_info
               SET value = ?
               WHERE key = ?'''
    cur = conn.cursor()
    cur.execute(sql, (value, key))
    conn.commit()
    return


if __name__ == '__main__':

    # Keep track of all players
    sql_create_player_table = create_table_sql_command("players", PLAYER_COLUMNS, PLAYER_COLUMNS_TYPES)

    # Keep track of Events
    sql_create_events_table = create_table_sql_command("events", EVENT_COLUMNS, EVENT_COLUMNS_TYPES)

    conn = create_connection(r"database/test_2.db")

    # create tables
    with conn:
        # create Player table
        create_table(conn, sql_create_player_table)
        # create Events table
        create_table(conn, sql_create_events_table)

        # delete table (for testing purposes)
        delete_all_players(conn)
        delete_all_events(conn)

        # -----------------------------------------------
        # create a new Player
        for i in tqdm(range(100)):
            player = (1234567890 + i, "Nama Zu", "PLD,DNC,SAM,MCH", datetime.today().strftime('%Y-%m-%d'), 0, 0)
            create_player(conn, player)

        # update player
        update_player(conn, "discord_id", 205335642287112192, 1234567902, "Nama Zu")
        update_player(conn, "character_name", "Na Mazu", 1234567904, "Nama Zu")
        update_player(conn, "jobs", "SAM", 1234567904, "Na Mazu")
        update_player(conn, "num_raids", 10, 1234567904, "Na Mazu")

        # delete player
        delete_player(conn, 1234567905, "Nama Zu")

        # fetch a player
        cur = conn.cursor()
        cur.execute("SELECT * FROM players WHERE discord_id=?", (1234567906,))

        rows = cur.fetchall()

        for row in rows:
            print(row)

        # -----------------------------------------------
        # create a new Event
        for i in tqdm(range(100)):
            event = ("Expert Roulette", int(time.time()), "A,B,C,D", "1,2,3,4", "0,0,0,0",
                     "PLD,SCH,MNK,RDM", "1,1,2", 205335642287112192, None,  "COMPLETED")
            create_event(conn, event)

        # update event
        update_event(conn, "name", "Leviathan (Unreal)", 3)
        update_event(conn, "participant_names", "A,B,C,D,E,F,G,H", 3)
        update_event(conn, "participant_ids", "1,2,3,4,5,6,7,8", 3)
        update_event(conn, "is_bench", col_str(["0" for _ in range(8)]), 3)
        update_event(conn, "jobs", "PLD,DRK,WHM,SCH,DRG,SAM,BLM,BRD", 3)
        update_event(conn, "role_numbers", "2,2,4", 3)
        update_event(conn, "state", "CANCELLED", 5)

        # delete event
        delete_event(conn, 7)

        # fetch last 5 events
        print("Last 1 events:")
        print(get_last_x_events(conn, 1))

        # find events
        tmp = find_events(conn, "name", "levi")
        print("Events with 'levi':", tmp)
