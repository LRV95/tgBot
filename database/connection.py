import sqlite3

def get_db_connection(db_path: str = "./database/database.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

