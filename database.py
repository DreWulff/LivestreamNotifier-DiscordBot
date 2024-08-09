import requests
import sqlite3
import os

CONNECTION = None

def execute_statement(statement) -> sqlite3.Cursor:
    """Tries to execute given unique statement."""
    global CONNECTION
    try:
        cursor = CONNECTION.cursor()
        cursor.execute(statement)
        CONNECTION.commit()
        return cursor
    except sqlite3.Error as e:
        print(e)
        return None

def connect_database(filename) -> sqlite3.Connection:
    """
    Create a database connection to an SQLite database.
    In case database doesn't exist, it is created.
    """
    conn = None
    try:
        conn = sqlite3.connect(filename)
        print(sqlite3.sqlite_version)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_channel_table() -> None:
    """Creates Twitch/YouTube tables in case it doesn't already exist in connected database."""
    sql_statement = f"""
        CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL,
                dschannel INTEGER NOT NULL,
                everyone BOOLEAN NOT NULL DEFAULT FALSE,
                islive BOOLEAN NOT NULL DEFAULT FALSE,
                livetitle TEXT,
                deleteflag BOOLEAN NOT NULL DEFAULT FALSE);
        """
    execute_statement(sql_statement)

def create_sub_table() -> None:
    """Creates subscriber table in case it doesn't already exist in connected database."""
    sql_statement = f"""
        CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL);
        """
    execute_statement(sql_statement)

def add_channel(channel, platform, dschannel) -> None:
    """
    Adds channel (row) to specified platform (table) in connected database.
    Name must be unique.
    """
    sql_statement = f"""
        INSERT INTO channels (
                name,
                platform,
                dschannel
            ) 
            VALUES 
                ('{channel}', '{platform}', {dschannel});
        """
    execute_statement(sql_statement)

def update_int_value(table, column, value, condition_column, condition) -> None:
    """Changes a value in the specified column and table given a condition."""
    sql_statement = f"""
        UPDATE {table}
        SET {column} = {value}
        WHERE {condition_column} = {condition};
        """
    execute_statement(sql_statement)

def update_str_value(table, column, value, condition_column, condition) -> None:
    """Changes a value in the specified column and table given a condition."""
    sql_statement = f"""
        UPDATE {table}
        SET {column} = '{value}'
        WHERE {condition_column} = {condition};
        """
    execute_statement(sql_statement)

def remove_channel(id) -> None:
    """Removes specified channel from table."""
    sql_statement = f"""
        DELETE FROM channels
        WHERE id = {id};
        """
    execute_statement(sql_statement)

def get_channels(platform=None) -> [sqlite3.Row]:
    """Gets list of channels in specified platform (table)."""
    sql_statement = f"""
        SELECT *
        FROM channels
        """
    if (platform != None):
        sql_statement += f"""
        WHERE platform = '{platform}'
        """
    sql_statement += ";"
    cursor = execute_statement(sql_statement)
    rows = cursor.fetchall()
    return rows

def get_channel(id) -> sqlite3.Row:
    """Gets data of channel by its id"""
    sql_statement = f"""
        SELECT *
        FROM channels
        WHERE id = {id};
        """
    cursor = execute_statement(sql_statement)
    rows = cursor.fetchall()
    row = rows[0] if len(rows) > 0 else None
    return row

def get_channel_by_name(name) -> sqlite3.Row:
    """Gets data of channel by its name"""
    sql_statement = f"""
        SELECT *
        FROM channels
        WHERE name = '{name}';
        """
    cursor = execute_statement(sql_statement)
    rows = cursor.fetchall()
    row = rows[0] if len(rows) > 0 else None
    return row

def get_subs(id) -> [sqlite3.Row]:
    """Get the list of subscribers of a specified channel."""
    sql_statement = f"""
        SELECT *
        FROM subscribers
        WHERE channel_id = {id};
        """
    cursor = execute_statement(sql_statement)
    subs = [sub[1] for sub in cursor.fetchall()]
    return subs

def remove_subs(channel_id) -> None:
    """Removes all subscribers for specified channel."""
    sql_statement = f"""
        DELETE FROM subscribers
        WHERE (channel_id = {channel_id});
        """
    execute_statement(sql_statement)

def get_subd(user_id) -> [sqlite3.Row]:
    """Get the list of subscribed channels of a user."""
    sql_statement = f"""
        SELECT channel_id
        FROM subscribers
        WHERE user_id = {user_id};
        """
    cursor = execute_statement(sql_statement)
    channel_ids = [row[0] for row in cursor.fetchall()]
    if (len(channel_ids) < 1):
        return None
    id_string = str(channel_ids[0])
    for id in channel_ids[1:]:
        id_string += ", " + str(id)

    sql_statement = f"""
        SELECT id, name
        FROM channels
        WHERE id IN ({id_string});
        """
    cursor = execute_statement(sql_statement)
    channels = cursor.fetchall()
    return channels

def get_unsubd(user_id) -> [sqlite3.Row]:
    """Get the list of unsubscribed channels of a user."""
    sql_statement = f"""
        SELECT channel_id
        FROM subscribers
        WHERE user_id = {user_id};
        """
    cursor = execute_statement(sql_statement)
    channel_ids = [row[0] for row in cursor.fetchall()]
    id_string = ""
    if (len(channel_ids) > 0):
        id_string = str(channel_ids[0])
        for id in channel_ids[1:]:
            id_string += ", " + str(id)

    sql_statement = f"""
        SELECT id, name
        FROM channels
        WHERE id NOT IN ({id_string});
        """
    cursor = execute_statement(sql_statement)
    channels = cursor.fetchall()
    return channels

def add_sub(user_id, channel_id) -> None:
    """Adds subscriber for specified channel."""
    sql_statement = f"""
        INSERT INTO subscribers (
                user_id,
                channel_id
            ) 
            VALUES 
                ({user_id}, {channel_id});
        """
    execute_statement(sql_statement)

def remove_sub(user_id, channel_id) -> None:
    """Removes subscriber for specified channel."""
    sql_statement = f"""
        DELETE FROM subscribers
        WHERE (user_id = {user_id} AND channel_id = {channel_id});
        """
    execute_statement(sql_statement)

def init_connection():
    global CONNECTION
    CONNECTION = connect_database("livestreams.db")

if __name__ == '__main__':
    init_connection()
    create_channel_table()
    create_sub_table()