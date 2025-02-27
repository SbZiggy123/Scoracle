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
                    username TEXT PRIMARY KEY UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    leagues TEXT DEFAULT '',
                    favourite_team TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # fantasy league table
            c.execute('''
                CREATE TABLE IF NOT EXISTS fantasyLeagues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league_name TEXT NOT NULL,
                    league_type TEXT CHECK(league_type IN ('classic', 'head2head')) NOT NULL,
                    privacy TEXT CHECK(privacy IN ('Public', 'Private')) NOT NULL,
                    league_code TEXT UNIQUE,
                    members TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # User predictions
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    match_id TEXT NOT NULL,
                    home_score INTEGER NOT NULL,
                    away_score INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    points_earned INTEGER DEFAULT NULL,
                    exact_score BOOLEAN DEFAULT FALSE,
                    correct_result BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE (user_id, match_id)
                )
            ''')
            
            """League members go here"""
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

def update_user(username, new_username, favourite_team):
    """Retrieve a user from the database and update user details based on dashboard form."""
    """Unfinished"""
    conn = get_db_connection()
    #Catch any errors finding users.
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
            c.execute('''
            UPDATE users 
            SET username = ?, favourite_team = ?
            WHERE username = ? 
            ''', (new_username, favourite_team, username))
            conn.close()    
    return None


def get_user_by_id(user_id):
    """Retrieve a user from the database by ID."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
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

""" USER PREDICTIONS FOR GAME SCORES"""
def save_prediction(user_id, match_id, home_score, away_score):
    """Save or update a user's prediction for a match."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Check if prediction already exists
            c.execute('SELECT id FROM user_predictions WHERE user_id = ? AND match_id = ?',
                     (user_id, match_id))
            existing = c.fetchone()
            
            if existing:
                # Update
                c.execute('''
                    UPDATE user_predictions 
                    SET home_score = ?, away_score = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (home_score, away_score, existing[0]))
            else:
                # Insert 
                c.execute('''
                    INSERT INTO user_predictions (user_id, match_id, home_score, away_score)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, match_id, home_score, away_score))
            
            conn.commit()
            return True
        except Error as e:
            print(f"Error saving prediction: {e}")
            return False
        finally:
            conn.close()
    return False

def get_user_predictions(user_id, limit=10):
    """Get the most recent predictions for a user."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM user_predictions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            predictions = c.fetchall()
            return [dict(prediction) for prediction in predictions]
        except Error as e:
            print(f"Error getting user predictions: {e}")
            return []
        finally:
            conn.close()
    return []


"""FANTASY LEAGUE"""

def add_fantasy_league(league_name, league_type, privacy, username):
    """Add a new fantasy league and assign the creator as the first member."""
    conn = get_db_connection()
    if conn is not None:
        try:
            league_code = generate_league_code() if privacy == "Private" else None

            c = conn.cursor()
            c.execute('''
                INSERT INTO fantasyLeagues (league_name, league_type, privacy, league_code, members)
                VALUES (?, ?, ?, ?, ?)
            ''', (league_name, league_type, privacy, league_code, str(username)))
            
            league_id = c.lastrowid

            c.execute("SELECT leagues FROM users WHERE username = ?", (username,))
            user_leagues = c.fetchone()[0]
            updated_leagues = f"{user_leagues},{league_id}".strip(",")
            c.execute("UPDATE users SET leagues = ? WHERE username = ?", (updated_leagues, username))

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

def get_league_by_id(league_id):
    """Fetch league details by ID."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM fantasyLeagues WHERE id = ?", (league_id,))
            league = c.fetchone()
            if league:
                return dict(league)
            return None
        except Error as e:
            print(f"Error fetching league: {e}")
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

def get_user_leagues(username):
    """Fetch all leagues the user is a part of."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT leagues FROM users WHERE username = ?", (username,))
            result = c.fetchone()

            if not result or not result[0]:
                return []

            league_ids = [int(x.strip()) for x in result[0].split(",") if x.strip() != ""]

            if not league_ids:
                return []

            placeholders = ','.join(['?'] * len(league_ids))
            query = f"SELECT id, league_name FROM fantasyLeagues WHERE id IN ({placeholders})"
            c.execute(query, league_ids)
            user_leagues = [{"id": row[0], "name": row[1]} for row in c.fetchall()]

            return user_leagues
        except Error as e:
            print(f"Error fetching user's leagues: {e}")
            return []
        finally:
            conn.close()
    return []

def is_user_in_league(username, league_id):
    """Check if a user is already in a league."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT members FROM fantasyLeagues WHERE id = ?", (league_id,))
            members = c.fetchone()[0]
            if str(username) in members.split(","):
                return True
            return False
        except Error as e:
            print(f"Error checking user in league: {e}")
            return False
        finally:
            conn.close()
    return False

def add_user_to_league(username, league_id):
    """Add a user to a league and update both users and fantasyLeagues tables."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()

            c.execute("SELECT members FROM fantasyLeagues WHERE id = ?", (league_id,))
            members = c.fetchone()[0]
            updated_members = f"{members},{username}".strip(",")
            c.execute("UPDATE fantasyLeagues SET members = ? WHERE id = ?", (updated_members, league_id))

            c.execute("SELECT leagues FROM users WHERE username = ?", (username,))
            user_leagues = c.fetchone()[0]
            updated_leagues = f"{user_leagues},{league_id}".strip(",")
            c.execute("UPDATE users SET leagues = ? WHERE username = ?", (updated_leagues, username))

            conn.commit()
            return True
        except Error as e:
            print(f"Error adding user to league: {e}")
            return False
        finally:
            conn.close()
    return False
