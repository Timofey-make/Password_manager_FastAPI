import sqlite3

def init_db():
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS passwords (
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL)
        ''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS share (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ownername INTEGER NOT NULL,
        sendername TEXT NOT NULL,
        name TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        conn.commit()