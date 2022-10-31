import sqlite3
import time


from config import SQL_PATH, NETWORKS


def connection_wrapper(func):
    def open_close_connection(*args, **kwargs):
        con = sqlite3.connect(SQL_PATH)
        cur = con.cursor()
        func(cur, *args, **kwargs)
        con.commit()
        con.close()
    return open_close_connection


@connection_wrapper
def create_table(cur):
    try:
        cur.execute('''CREATE TABLE networks_info(
            network text UNIQUE, 
            apr number, 
            delegators number, 
            denom text, 
            health number,
            place number,
            tokens number,
            price number
        )''')
        for n in NETWORKS:
            data = (n['name'], None, None, None, None, None, None, None)
            try:
                cur.execute("insert into networks_info values (?, ?, ?, ?, ?, ?, ?, ?)", tuple(data))
            except (sqlite3.IntegrityError, sqlite3.OperationalError) as er:
                pass
    except (sqlite3.IntegrityError, sqlite3.OperationalError) as er:
        for n in NETWORKS:
            data = (n['name'], None, None, None, None, None, None, None)
            try:
                cur.execute("insert into networks_info values (?, ?, ?, ?, ?, ?, ?, ?)", tuple(data))
            except (sqlite3.IntegrityError, sqlite3.OperationalError) as er:
                pass
        pass


@connection_wrapper
def set_value_by_network(cur, network, column, value):
    cur.execute(f"UPDATE networks_info set {column} = ? where network = ?",
                (value, network))


@connection_wrapper
def set_value_by_api(cur, network, column, value):
    cur.execute(f"UPDATE prices set {column} = ? where network = ?",
                (value, network))


@connection_wrapper
def save_to_db(cur, data):
    cur.execute("insert into networks_info values (?, ?, ?, ?, ?, ?, ?)", tuple(data))


def get_all_rows():
    con = sqlite3.connect(SQL_PATH)
    cur = con.cursor()
    cur.execute("SELECT * FROM networks_info")
    fetched_data = cur.fetchall().copy()
    con.commit()
    con.close()
    return fetched_data


def get_prices():
    con = sqlite3.connect(SQL_PATH)
    cur = con.cursor()
    cur.execute("SELECT * FROM prices")
    fetched_data = cur.fetchall().copy()
    con.commit()
    con.close()
    return fetched_data