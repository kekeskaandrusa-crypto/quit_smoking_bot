import sqlite3

def get_db():
    return sqlite3.connect("database.db")

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        price INTEGER DEFAULT 0,
        last_smoke_date TEXT,
        streak INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marks (
        user_id INTEGER,
        date TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, price, last_smoke_date, streak FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        conn.commit()
        cursor.execute("SELECT id, price, last_smoke_date, streak FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def update_user(user_id, price=None, last_date=None, streak=None):
    conn = get_db()
    cursor = conn.cursor()
    if price is not None:
        cursor.execute("UPDATE users SET price=? WHERE id=?", (price, user_id))
    if last_date is not None:
        cursor.execute("UPDATE users SET last_smoke_date=? WHERE id=?", (last_date, user_id))
    if streak is not None:
        cursor.execute("UPDATE users SET streak=? WHERE id=?", (streak, user_id))
    conn.commit()
    conn.close()

def add_mark(user_id, date):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO marks (user_id, date) VALUES (?, ?)", (user_id, date))
    conn.commit()
    conn.close()
