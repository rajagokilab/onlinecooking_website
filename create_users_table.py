import sqlite3

def create_users_table():
    conn = sqlite3.connect('users.db')  # This creates the database file if it doesn't exist
    cursor = conn.cursor()

    # Create the users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT,
        mobile TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print("Users table created successfully in users.db")

if __name__ == "__main__":
    create_users_table()
