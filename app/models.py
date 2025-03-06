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
                    leagues TEXT DEFAULT '',
                    favourite_team TEXT DEFAULT '',
                    profile_pic TEXT DEFAULT 'login.png',
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
                    multiplier REAL DEFAULT 1.0,
                    potential_exact_points INTEGER DEFAULT 100,
                    potential_result_points INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    points_earned INTEGER DEFAULT NULL,
                    exact_score BOOLEAN DEFAULT FALSE,
                    correct_result BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE (user_id, match_id)
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_player_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    match_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    goals_prediction INTEGER DEFAULT 0,
                    shots_prediction INTEGER DEFAULT 0,
                    minutes_prediction INTEGER DEFAULT 0,
                    multiplier REAL DEFAULT 1.0,
                    potential_points INTEGER DEFAULT 100,
                    points_earned INTEGER DEFAULT NULL,
                    prediction_correct BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE (user_id, match_id, player_id)
                )
            ''')
            
            #League Specific User Scores
            c.execute('''
                CREATE TABLE IF NOT EXISTS league_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    league_id INTEGER NOT NULL,
                    score INTEGER DEFAULT 1000,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (league_id) REFERENCES fantasyLeagues (id),
                    UNIQUE (user_id, league_id)
                )
            ''')
            c.execute('''        
                CREATE TABLE IF NOT EXISTS LeagueBets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    league_id INTEGER NOT NULL,
                    match_id TEXT NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    prediction TEXT CHECK(prediction IN ('home', 'away', 'draw')) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (league_id) REFERENCES fantasyLeagues (id)
                )'''
            )
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

def update_user(username, update_field, update_item):
    """Retrieve a user from the database and update user details based on dashboard form."""
    conn = get_db_connection()
    #Catch any errors finding users.
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username))
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
            SET ? = ?,
            WHERE username = ?, 
            ''', (update_field, update_item, username))
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
def save_prediction(user_id, match_id, home_score, away_score, multiplier=1.0, potential_exact_points=100, potential_result_points=100):
    """Save or update a user's prediction for a match."""
    import traceback
    print(f"DEBUG save_prediction: user_id={user_id}, match_id={match_id}, scores={home_score}-{away_score}")
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Check if prediction already exists
            c.execute('SELECT id FROM user_predictions WHERE user_id = ? AND match_id = ?',
                     (user_id, match_id))
            existing = c.fetchone()
            
            print(f"DEBUG: Existing prediction found? {bool(existing)}")
            
            if existing:
                # Update
                print(f"DEBUG: Updating prediction with ID: {existing[0]}")
                update_sql = '''
                    UPDATE user_predictions 
                    SET home_score = ?, away_score = ?, multiplier = ?, 
                    potential_exact_points = ?, potential_result_points = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                '''
                params = (home_score, away_score, multiplier, potential_exact_points, potential_result_points, existing[0])
                print(f"DEBUG: SQL: {update_sql}")
                print(f"DEBUG: Params: {params}")
                c.execute(update_sql, params)
            else:
                # Insert with all fields
                insert_sql = '''
                    INSERT INTO user_predictions
                    (user_id, match_id, home_score, away_score, multiplier, potential_exact_points, potential_result_points)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                '''
                params = (user_id, match_id, home_score, away_score, multiplier, potential_exact_points, potential_result_points)
                print(f"DEBUG: SQL: {insert_sql}")
                print(f"DEBUG: Params: {params}")
                c.execute(insert_sql, params)
            
            conn.commit()
            print("DEBUG: Database committed successfully")
            return True
        except Exception as e:
            print(f"ERROR saving prediction: {e}")
            print(traceback.format_exc())
            return False
        finally:
            conn.close()
    print("ERROR: Could not get database connection")
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

def save_player_prediction(user_id, match_id, player_id, goals_prediction, shots_prediction, minutes_prediction, 
                         multiplier=1.0, potential_points=100):
    """Save or update a user's player prediction."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Check if prediction already exists
            c.execute('''SELECT id FROM user_player_predictions 
                         WHERE user_id = ? AND match_id = ? AND player_id = ?''',
                     (user_id, match_id, player_id))
            existing = c.fetchone()
            
            if existing:
                # Update
                update_sql = '''
                    UPDATE user_player_predictions 
                    SET goals_prediction = ?, shots_prediction = ?, minutes_prediction = ?,
                        multiplier = ?, potential_points = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                '''
                params = (goals_prediction, shots_prediction, minutes_prediction,
                         multiplier, potential_points, existing[0])
                c.execute(update_sql, params)
            else:
                # Insert new prediction
                insert_sql = '''
                    INSERT INTO user_player_predictions
                    (user_id, match_id, player_id, goals_prediction, shots_prediction, 
                     minutes_prediction, multiplier, potential_points)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (user_id, match_id, player_id, goals_prediction, shots_prediction,
                         minutes_prediction, multiplier, potential_points)
                c.execute(insert_sql, params)
            
            conn.commit()
            return True
        except Exception as e:
            print(f"ERROR saving player prediction: {e}")
            import traceback
            print(traceback.format_exc())
            return False
        finally:
            conn.close()
    return False

def get_user_player_predictions(user_id, match_id=None):
    """Get player predictions for a user, optionally filtered by match."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            if match_id:
                # Get predictions for  match
                c.execute('''
                    SELECT * FROM user_player_predictions
                    WHERE user_id = ? AND match_id = ?
                    ORDER BY created_at DESC
                ''', (user_id, match_id))
            else:
                # Get all player predictions
                c.execute('''
                    SELECT * FROM user_player_predictions
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
                
            predictions = c.fetchall()
            return [dict(prediction) for prediction in predictions]
        except Error as e:
            print(f"Error getting user player predictions: {e}")
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
            result = c.fetchone()

            if result and result[0]:
                members = result[0].split(",")
                return username in members

            return False
        except Error as e:
            print(f"Error checking if user is in league: {e}")
            return False
        finally:
            conn.close()
    return False

def add_user_to_league(username, league_id):
    """Add a user to a league and ensure they have a score entry, updating the user's leagues column."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()

            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_row = c.fetchone()
            if not user_row:
                return False
            user_id = user_row[0]

            c.execute("SELECT members FROM fantasyLeagues WHERE id = ?", (league_id,))
            members_row = c.fetchone()
            members = members_row[0].split(",") if members_row and members_row[0] else []
            
            if username in members:
                return False 

            members.append(username)
            updated_members = ",".join(members)
            c.execute("UPDATE fantasyLeagues SET members = ? WHERE id = ?", (updated_members, league_id))

            c.execute("SELECT leagues FROM users WHERE username = ?", (username,))
            user_leagues_row = c.fetchone()
            user_leagues = user_leagues_row[0] if user_leagues_row and user_leagues_row[0] else ""
            updated_user_leagues = f"{user_leagues},{league_id}".strip(",")
            c.execute("UPDATE users SET leagues = ? WHERE username = ?", (updated_user_leagues, username))

            c.execute("INSERT OR IGNORE INTO league_scores (user_id, league_id, score) VALUES (?, ?, 1000)", 
                      (user_id, league_id))

            conn.commit()
            return True
        except Error as e:
            print(f"Error adding user to league: {e}")
            return False
        finally:
            conn.close()
    return False


def get_league_leaderboard(league_id):
    """Fetch the leaderboard for a specific league"""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            # Get all members of the league
            c.execute("SELECT members FROM fantasyLeagues WHERE id = ?", (league_id,))
            members_str = c.fetchone()
            if not members_str or not members_str[0]:
                return []

            member_list = [x.strip() for x in members_str[0].split(",") if x.strip()]

            # Fetch user IDs for these members
            placeholders = ','.join(['?'] * len(member_list))
            c.execute(f"SELECT id, username FROM users WHERE username IN ({placeholders})", member_list)
            users = {row[0]: row[1] for row in c.fetchall()}  # Dict {user_id: username}

            # Fetch existing scores from league_scores
            c.execute("SELECT user_id, score FROM league_scores WHERE league_id = ?", (league_id,))
            existing_scores = {row[0]: row[1] for row in c.fetchall()}  # Dict {user_id: score}

            # Build the leaderboard
            leaderboard = []
            for user_id, username in users.items():
                score = existing_scores.get(user_id, 0)  # Default to 0 if no score exists
                leaderboard.append({"username": username, "score": score})

            # Sort by score (highest first)
            leaderboard.sort(key=lambda x: x["score"], reverse=True)

            return leaderboard
        except Error as e:
            print(f"Error fetching leaderboard: {e}")
            return []
        finally:
            conn.close()
    return []

def update_league_score(user_id, league_id, points):
    """Update a user's score in a specific league."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()

            # Check if the user already has a score in this league
            c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = ?", (user_id, league_id))
            result = c.fetchone()

            if result:
                # Update existing score
                new_score = result[0] + points
                c.execute("UPDATE league_scores SET score = ? WHERE user_id = ? AND league_id = ?", 
                          (new_score, user_id, league_id))
            else:
                # Insert new score entry
                c.execute("INSERT INTO league_scores (user_id, league_id, score) VALUES (?, ?, ?)", 
                          (user_id, league_id, points))

            conn.commit()
            return True
        except Error as e:
            print(f"Error updating league score: {e}")
            return False
        finally:
            conn.close()
    return False

def place_bet(user_id, league_id, match_id, bet_amount, prediction):
    """Allows a user to place a bet on a match using their league score as currency."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            # Check if the user has enough points
            c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = ?", (user_id, league_id))
            user_score = c.fetchone()
            
            if not user_score or user_score[0] < bet_amount:
                return {"success": False, "message": "Insufficient points to place bet"}
            
            # Deduct points from the user's score
            new_score = user_score[0] - bet_amount
            c.execute("UPDATE league_scores SET score = ? WHERE user_id = ? AND league_id = ?", 
                      (new_score, user_id, league_id))

            # Insert the bet into the table
            c.execute('''
                INSERT INTO LeagueBets (user_id, league_id, match_id, bet_amount, prediction)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, league_id, match_id, bet_amount, prediction))
            
            conn.commit()
            return {"success": True, "message": "Bet placed successfully"}
        except Exception as e:
            print(f"Error placing bet: {e}")
            return {"success": False, "message": "Error placing bet"}
        finally:
            conn.close()
    return {"success": False, "message": "Database connection failed"}

def process_match_bets(match_id, home_goals, away_goals):
    """Process all bets for a given match and update user scores accordingly."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Determine match outcome
            if home_goals > away_goals:
                actual_result = "home"
            elif away_goals > home_goals:
                actual_result = "away"
            else:
                actual_result = "draw"
            
            # Fetch bets for this match
            c.execute("SELECT id, user_id, league_id, bet_amount, prediction FROM bets WHERE match_id = ?", (match_id,))
            bets = c.fetchall()
            
            for bet in bets:
                bet_id, user_id, league_id, bet_amount, prediction = bet
                if prediction == actual_result:
                    winnings = bet_amount * 2  # Example: payout is 2x the bet
                    c.execute(
                        "UPDATE league_scores SET score = score + ? WHERE user_id = ? AND league_id = ?",
                        (winnings, user_id, league_id)
                    )
                # Remove the processed bet
                c.execute("DELETE FROM bets WHERE id = ?", (bet_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error processing match bets: {e}")
            return False
        finally:
            conn.close()
    return False

def get_user_bets(user_id, league_id):
    """Fetch all bets for a given user and league."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM bets WHERE user_id = ? AND league_id = ?", (user_id, league_id))
            bets = c.fetchall()
            return [dict(bet) for bet in bets]
        except Exception as e:
            print(f"Error fetching user bets: {e}")
            return []
        finally:
            conn.close()
    return []