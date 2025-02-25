import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

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
            # fantasy league table(more to be added after log in is sorted)
            c.execute('''
                CREATE TABLE IF NOT EXISTS fantasyLeagues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league_name TEXT NOT NULL,
                    league_type TEXT CHECK(league_type IN ('classic', 'head2head')) NOT NULL,
                    privacy TEXT CHECK(privacy IN ('Public', 'Private')) NOT NULL,
                    league_code TEXT UNIQUE,
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

def add_fantasy_league(league_name, league_type, privacy):
    """Add a new fantasy league to the database. adds code if its private. otherwise doesnt."""
    conn = get_db_connection()
    if conn is not None:
        try:
            league_code = generate_league_code() if privacy == "Private" else None

            c = conn.cursor()
            c.execute('''
                INSERT INTO fantasyLeagues (league_name, league_type, privacy, league_code)
                VALUES (?, ?, ?, ?)
            ''', (league_name, league_type, privacy, league_code))
            conn.commit()
            return league_code if league_code else True
        except Error as e:
            print(f"Error adding fantasy league: {e}")
            return False
        finally:
            conn.close()
    return False

def get_league_by_code(league_code):
    """Fetch a private league by its unique code."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT id, league_name FROM fantasyLeagues WHERE league_code = ?", (league_code,))
            league = c.fetchone()
            if league:
                return {"id": league[0], "league_name": league[1]}
            return None
        except Error as e:
            print(f"Error fetching private league: {e}")
            return None
        finally:
            conn.close()
    return None

def get_public_leagues():
    """Fetch all public fantasy leagues from the database."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT id, league_name FROM fantasyLeagues WHERE privacy = 'Public'")
            leagues = c.fetchall()
            return [{"id": row[0], "name": row[1]} for row in leagues]
        except Error as e:
            print(f"Error fetching public leagues: {e}")
            return []
        finally:
            conn.close()
    return []

def generate_league_code():
    """Generate a random 6-character league code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))