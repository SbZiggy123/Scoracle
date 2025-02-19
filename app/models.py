import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'scoracle.db'

def get_db_connection():
    """Create a database connection."""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def init_db():
    """Initialize the database with the users table."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Create users table
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        except Error as e:
            print(f"Error creating database: {e}")
        finally:
            conn.close()

def add_user(username, password):
    """Add a new user to the database."""
    conn = get_db_connection()
    if conn is not None:
        try:
            password_hash = generate_password_hash(password)
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                     (username, password_hash))
            conn.commit()
            return True
        except Error as e:
            print(f"Error adding user: {e}")
            return False
        finally:
            conn.close()
    return False

def get_user(username):
    """Retrieve a user from the database."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = c.fetchone()
            if user:
                return dict(user)
            return None
        except Error as e:
            print(f"Error retrieving user: {e}")
            return None
        finally:
            conn.close()
    return None

def verify_password(username, password):
    user = get_user(username)
    if user:
        return check_password_hash(user["password_hash"], password)

def user_exists(username):
    """Check if a username already exists."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
            return c.fetchone() is not None
        except Error as e:
            print(f"Error checking user existence: {e}")
            return False
        finally:
            conn.close()
    return False