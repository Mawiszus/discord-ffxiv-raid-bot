import sqlite3
from sqlite3 import Error
from datetime import datetime
import time
from tqdm import tqdm

PLAYER_COLUMNS = ["discord_id", "character_name", "jobs", "num_raids"]
EVENT_COLUMNS = ["name", "timestamp", "participant_names", "participant_ids", "jobs", "state"]


def create_connection(db_file: str):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
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
    sql = ''' INSERT INTO players(discord_id,character_name,jobs,signup_date,num_raids)
              VALUES(?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, player)
    conn.commit()
    return cur.lastrowid


def get_player(conn, discord_id, name):
    """Find the player given id and name"""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM players WHERE discord_id=? AND character_name=?", (discord_id, name))
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
    sql = ''' INSERT INTO events(name,timestamp,participant_names,participant_ids,jobs,state)
              VALUES(?,?,?,?,?,?) '''
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


if __name__ == '__main__':

    # Keep track of all players
    sql_create_player_table = """ CREATE TABLE IF NOT EXISTS players (
                                        id integer PRIMARY KEY,
                                        discord_id integer NOT NULL,
                                        character_name text NOT NULL,
                                        jobs text,
                                        signup_date text,
                                        num_raids integer
                                    ); """

    # Keep track of Events
    sql_create_events_table = """ CREATE TABLE IF NOT EXISTS events (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        timestamp integer NOT NULL,
                                        participant_names text,
                                        participant_ids text,
                                        jobs text,
                                        state text NOT NULL
                                    ); """

    conn = create_connection(r"database/test.db")

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
            player = (1234567890 + i, "Nama Zu", "PLD,DNC,SAM,MCH", datetime.today().strftime('%Y-%m-%d'), 0)
            create_player(conn, player)

        # update player
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
            event = ("Expert Roulette", int(time.time()), "A,B,C,D", "1,2,3,4", "PLD,SCH,MNK,RDM", "COMPLETED")
            create_event(conn, event)

        # update event
        update_event(conn, "name", "Leviathan (Unreal)", 3)
        update_event(conn, "participant_names", "A,B,C,D,E,F,G,H", 3)
        update_event(conn, "participant_ids", "1,2,3,4,5,6,7,8", 3)
        update_event(conn, "jobs", "PLD,DRK,WHM,SCH,DRG,SAM,BLM,BRD", 3)
        update_event(conn, "state", "CANCELLED", 5)

        # delete event
        delete_event(conn, 7)

        # fetch last 5 events
        print("Last 1 events:")
        print(get_last_x_events(conn, 1))

        # find events
        tmp = find_events(conn, "name", "levi")
        print("Events with 'levi':", tmp)
