import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from datetime import datetime, timedelta

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
                    profile_pic TEXT NOT NULL DEFAULT 'login.png',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # fantasy league table
            c.execute('''
                CREATE TABLE IF NOT EXISTS fantasyLeagues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league_name TEXT NOT NULL,
                    league_type TEXT CHECK(league_type IN ('classic', 'seasonal')) NOT NULL,
                    privacy TEXT CHECK(privacy IN ('Public', 'Private')) NOT NULL,
                    league_code TEXT UNIQUE,
                    members TEXT DEFAULT '',
                    creator TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    season_end TIMESTAMP DEFAULT NULL
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
                    league_id INTEGER DEFAULT 1,
                    bet_amount INTEGER DEFAULT 0,
                    outcome_prediction TEXT DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (league_id) REFERENCES fantasyLeagues (id)
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
                    league_id INTEGER DEFAULT 1,
                    bet_amount INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (league_id) REFERENCES fantasyLeagues (id)
                )
            ''')
            
            #League Specific User Scores
            c.execute('''
                CREATE TABLE IF NOT EXISTS league_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    league_id INTEGER NOT NULL,
                    score INTEGER DEFAULT 1000,
                    trophies INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (league_id) REFERENCES fantasyLeagues (id),
                    UNIQUE (user_id, league_id)
                )
            ''')
            conn.commit()
            
            # Create global league
            ensure_global_league_exists()
            
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
    if conn is not None:
        try:
            c = conn.cursor()
            allowed_fields = {"username", "favourite_team", "profile_pic"} 
            if update_field not in allowed_fields:
                raise ValueError("Invalid field name!")
            query = f"UPDATE users SET {update_field} = ? WHERE username = ?"
            c.execute(query, (update_item, username))
            conn.commit()
        except Error as e:
            print(f"Error updating user: {e}")
            return None
        finally:
            if conn:
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
def save_prediction(user_id, match_id, home_score, away_score, bet_amount, outcome_prediction, multiplier=1.0, potential_exact_points=100, potential_result_points=100):
    """Save or update a user's prediction for a match. outcome prediction is for win/loss bets. score predicting bets leave it null."""
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
                    SET home_score = ?, away_score = ?, bet_amount = ?, outcome_prediction = ?, multiplier = ?, potential_exact_points = ?, potential_result_points = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                '''
                params = (home_score, away_score, bet_amount, outcome_prediction, multiplier, potential_exact_points, potential_result_points, existing[0])
                print(f"DEBUG: SQL: {update_sql}")
                print(f"DEBUG: Params: {params}")
                c.execute(update_sql, params)
            else:
                # Insert with all fields
                insert_sql = '''
                    INSERT INTO user_predictions
                    (user_id, match_id, home_score, away_score, bet_amount, outcome_prediction, multiplier, potential_exact_points, potential_result_points)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (user_id, match_id, home_score, away_score, bet_amount, outcome_prediction, multiplier, potential_exact_points, potential_result_points)
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

def save_player_prediction(user_id, match_id, player_id, goals_prediction, shots_prediction, minutes_prediction=0, 
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
                INSERT INTO fantasyLeagues (league_name, league_type, privacy, league_code, members, creator, season_end)
                VALUES (?, ?, ?, ?, ?, ?, null)
            ''', (league_name, league_type, privacy, league_code, str(username), str(username)))
            league_id = c.lastrowid
            
            #set league end for 1 week from creation
            if league_type == "seasonal":
                season_end = (datetime.now() + timedelta(weeks=1)).isoformat(sep=' ', timespec='seconds')
                c.execute('''
                    UPDATE fantasyLeagues 
                    SET season_end = ?
                    WHERE id = ?
                ''', (season_end, league_id))

            # Update the creator's leagues column
            c.execute("SELECT leagues FROM users WHERE username = ?", (username,))
            user_leagues = c.fetchone()[0]
            updated_leagues = f"{user_leagues},{league_id}".strip(",")
            c.execute("UPDATE users SET leagues = ? WHERE username = ?", (updated_leagues, username))
            
            # Insert the creator into league_scores with a starting score of 1000
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_row = c.fetchone()
            if user_row:
                user_id = user_row[0]
                c.execute("INSERT INTO league_scores (user_id, league_id, score) VALUES (?, ?, 1000)", (user_id, league_id))
            
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
    """Fetch league details by ID"""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM fantasyLeagues WHERE id = ?", (league_id,))
            row = c.fetchone()
            if row:
                league = dict(row)
                return league
            return None
        except Error as e:
            print(f"Error fetching league: {e}")
            return None
        finally:
            conn.close()
    return None

def get_public_leagues():
    """Fetch all public fantasy leagues with creator names."""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("""
                SELECT f.id, f.league_name, f.league_type, f.privacy, f.members, f.created_at, u.username as creator
                FROM fantasyLeagues f
                JOIN users u ON f.members LIKE u.username || '%'  -- Get the first user in the members list
                WHERE f.privacy = 'Public'
            """)
            leagues = c.fetchall()
            return [{"id": row[0], "name": row[1], "league_type": row[2], "members": row[4], "created_at": row[5], "creator": row[6]} for row in leagues]
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
    """Fetch all leagues the user is a part of"""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT leagues FROM users WHERE username = ?", (username,))
            result = c.fetchone()

            if not result or not result[0]:
                return []

            league_ids = [int(x.strip()) for x in result[0].split(",") if x.strip()]

            if not league_ids:
                return []

            placeholders = ",".join(["?"] * len(league_ids))

            query = f"""
                SELECT f.id, f.league_name, f.league_type, f.privacy, f.members, f.created_at, u.username as creator
                FROM fantasyLeagues f
                JOIN users u ON f.members LIKE u.username || '%'
                WHERE f.id IN ({placeholders})
            """
            c.execute(query, league_ids)
            rows = c.fetchall()

            user_leagues = [
                {
                    "id": row[0],
                    "name": row[1],
                    "league_type": row[2],
                    "privacy": row[3],
                    "members": row[4],
                    "created_at": row[5],
                    "creator": row[6]
                }
                for row in rows
            ]

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

            # Get the user_id
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_row = c.fetchone()
            if not user_row:
                return False
            user_id = user_row[0]

            # Update league members list
            c.execute("SELECT members FROM fantasyLeagues WHERE id = ?", (league_id,))
            members_row = c.fetchone()
            members = members_row[0].split(",") if members_row and members_row[0] else []
            if username in members:
                return False 
            members.append(username)
            updated_members = ",".join(members)
            c.execute("UPDATE fantasyLeagues SET members = ? WHERE id = ?", (updated_members, league_id))

            # Update user's leagues column
            c.execute("SELECT leagues FROM users WHERE username = ?", (username,))
            user_leagues_row = c.fetchone()
            user_leagues = user_leagues_row[0] if user_leagues_row and user_leagues_row[0] else ""
            updated_user_leagues = f"{user_leagues},{league_id}".strip(",")
            c.execute("UPDATE users SET leagues = ? WHERE username = ?", (updated_user_leagues, username))

            # Check if a league_scores row exists
            c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = ?", (user_id, league_id))
            existing = c.fetchone()
            if existing is None:
                # Insert new row with a starting score of 1000
                c.execute("INSERT INTO league_scores (user_id, league_id, score) VALUES (?, ?, 1000)", 
                          (user_id, league_id))
            else:
                # Update existing row to have a score of 1000 (if needed)
                c.execute("UPDATE league_scores SET score = 1000 WHERE user_id = ? AND league_id = ?", 
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

def get_seasonal_league_leaderboard(league_id):
    """Fetch the leaderboard for a specific seasonal league"""
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
            
            # Fetch existing trophies from league_scores
            c.execute("SELECT user_id, trophies FROM league_scores WHERE league_id = ?", (league_id,))
            existing_trophies = {row[0]: row[1] for row in c.fetchall()}  # Dict {user_id: trophies}

            # Build the leaderboard
            leaderboard = []
            for user_id, username in users.items():
                score = existing_scores.get(user_id, 0)
                trophies = existing_trophies.get(user_id, 0) 
                leaderboard.append({"username": username, "score": score, "trophies": trophies})

            # Sort by score (highest first)
            leaderboard.sort(key=lambda x: x["score"], reverse=True)

            return leaderboard
        except Error as e:
            print(f"Error fetching leaderboard: {e}")
            return []
        finally:
            conn.close()
    return []


def end_seasonal_round(league_id):
    """End the current seasonal round, award a trophy to the top scorer, reset all users' scores, and set a new season_end for next round. """
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()

            # Find the maximum score in the league
            c.execute("""
                SELECT MAX(score) 
                FROM league_scores
                WHERE league_id = ?
            """, (league_id,))
            max_score_result = c.fetchone()
            if not max_score_result or max_score_result[0] is None:
                # No rows or no valid score
                conn.close()
                return False

            max_score = max_score_result[0]

            #Award trophies to all users with top score
            c.execute("""
                UPDATE league_scores
                SET trophies = trophies + 1
                WHERE league_id = ?
                  AND score = ?
            """, (league_id, max_score))

            # Reset everyone's score to 1000
            c.execute("""
                UPDATE league_scores
                SET score = 1000
                WHERE league_id = ?
            """, (league_id,))

            # Set the new season_end to one week from now
            new_end_dt = datetime.now() + timedelta(weeks=1)
            new_end_str = new_end_dt.strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                UPDATE fantasyLeagues
                SET season_end = ?
                WHERE id = ?
            """, (new_end_str, league_id))

            conn.commit()
            return True
        except Error as e:
            print(f"Error ending seasonal round for league {league_id}: {e}")
            return False
        finally:
            conn.close()
    return False


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

def place_bet(user_id, league_id, match_id, bet_amount, outcome_prediction=None, home_score=0, away_score=0):
    """ Place a bet by saving it in the unified user_predictions table. """
    
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            # Check if the user has enough points
            c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = ?", (user_id, league_id))
            user_score = c.fetchone()
            if not user_score or user_score[0] < bet_amount:
                return {"success": False, "message": "Insufficient points to place bet"}
            
            # Deduct the bet amount from the user's score
            new_score = user_score[0] - bet_amount
            c.execute("UPDATE league_scores SET score = ? WHERE user_id = ? AND league_id = ?", 
                      (new_score, user_id, league_id))
            
            # Decide which type of bet this is
            if outcome_prediction is not None:
                # Outcome bet: ignore exact score predictions.
                home_score = 0
                away_score = 0
            else:
                # Exact score prediction bet: outcome_prediction remains NULL.
                outcome_prediction = None  # Explicitly set for clarity
            
            # Insert the bet into the unified table
            c.execute('''
                INSERT INTO user_predictions
                (user_id, match_id, home_score, away_score, bet_amount, outcome_prediction)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, match_id, home_score, away_score, bet_amount, outcome_prediction))
            
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
            if home_goals > away_goals:
                actual_result = "home"
            elif away_goals > home_goals:
                actual_result = "away"
            else:
                actual_result = "draw"
                
            c.execute("SELECT id, user_id, league_id, bet_amount, outcome_prediction, home_score, away_score FROM user_predictions WHERE match_id = ?", (match_id,))
            predictions = c.fetchall()
            
            for pred in predictions:
                bet_id, user_id, league_id, bet_amount, outcome_prediction, home_score, away_score = pred
                # Win/loss predictions
                if outcome_prediction is not None:
                    if outcome_prediction == actual_result:
                        winnings = bet_amount * 3
                        c.execute(
                            "UPDATE league_scores SET score = score + ? WHERE user_id = ? AND league_id = ?",
                            (winnings, user_id, league_id)
                        )
                    c.execute("DELETE FROM user_predictions WHERE id = ?", (bet_id,))
                else:
                    #Exact Score predictions
                    if home_score == home_goals and away_score == away_goals:
                        winnings = bet_amount * 5
                        c.execute(
                            "UPDATE league_scores SET score = score + ? WHERE user_id = ? AND league_id = ?",
                            (winnings, user_id, league_id)
                        )
                    elif (home_score > away_score and home_goals > away_goals) or (away_score > home_score and away_goals > home_goals) or (home_score == away_score and home_goals == away_goals):
                        # Award a lower payout for a correct outcome only
                        winnings = bet_amount * 2
                        c.execute(
                            "UPDATE league_scores SET score = score + ? WHERE user_id = ? AND league_id = ?",
                            (winnings, user_id, league_id)
                        )
            
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

def get_profile_pic(user):
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT profile_pic FROM users WHERE username = ?", (user,))
            profile_pic = c.fetchone()
            if profile_pic:
                profile_pic = profile_pic[0]
                profile_pic = "/static/profilepics/" + profile_pic
        except Error as e:
            print(f"Error fetching profile picture: {e}")
            return False
        finally:
            conn.close()
    return profile_pic

def ensure_global_league_exists():
    """
    Make sure the global league exists in the database.
    """
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            # Check if global league exists (ID = 1)
            c.execute("SELECT id FROM fantasyLeagues WHERE id = 1")
            global_league = c.fetchone()
            
            if not global_league:
                # Create global league if it doesn't exist
                c.execute('''
                    INSERT INTO fantasyLeagues 
                    (id, league_name, league_type, privacy, members) 
                    VALUES (1, 'Global Ranking', 'classic', 'Public', '')
                ''')
                conn.commit()
                print("Created Global Ranking league")
            
            return True
        except Error as e:
            print(f"Error ensuring global league exists: {e}")
            return False
        finally:
            conn.close()
    return False

def ensure_user_in_global_league(user_id, username):
    """
    Make sure the user is part of the global league.
    Called when a user logs in or registers.
    """
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            # Check if user is in global league scores
            c.execute("SELECT id FROM league_scores WHERE user_id = ? AND league_id = 1", (user_id,))
            user_score = c.fetchone()
            
            if not user_score:
                # Add user to global league scores with starting score
                c.execute("INSERT INTO league_scores (user_id, league_id, score) VALUES (?, 1, 1000)", (user_id,))
                
                # Update global league members
                c.execute("SELECT members FROM fantasyLeagues WHERE id = 1")
                members_row = c.fetchone()
                members = members_row[0].split(",") if members_row and members_row[0] else []
                
                if username not in members:
                    members.append(username)
                    updated_members = ",".join(members)
                    c.execute("UPDATE fantasyLeagues SET members = ? WHERE id = 1", (updated_members,))
                
                # Add global league to user's leagues
                c.execute("SELECT leagues FROM users WHERE id = ?", (user_id,))
                leagues_row = c.fetchone()
                user_leagues = leagues_row[0] if leagues_row and leagues_row[0] else ""
                
                if "1" not in user_leagues.split(","):
                    updated_leagues = f"{user_leagues},1".strip(",")
                    c.execute("UPDATE users SET leagues = ? WHERE id = ?", (updated_leagues, user_id))
                
                conn.commit()
            
            return True
        except Error as e:
            print(f"Error adding user to global league: {e}")
            return False
        finally:
            conn.close()
    return False


#head2head mode functions
def end_week_for_league(league_id):
    """
    Identify the top scorer in the league, increment their trophy count,
    then reset all scores to 1000.
    """
    conn = get_db_connection()
    if conn:
        try:
            c = conn.cursor()
            # 1. Find the user_id with the highest score
            c.execute("""
                SELECT user_id, score
                FROM league_scores
                WHERE league_id = ?
                ORDER BY score DESC
                LIMIT 1
            """, (league_id,))
            top_user = c.fetchone()
            
            if top_user:
                top_user_id, top_score = top_user
                # 2. Increment their trophy count
                c.execute("""
                    UPDATE league_scores
                    SET trophies = trophies + 1
                    WHERE user_id = ? AND league_id = ?
                """, (top_user_id, league_id))
            
            # 3. Reset scores to 0 for everyone
            c.execute("""
                UPDATE league_scores
                SET score = 1000
                WHERE league_id = ?
            """, (league_id,))
            
            conn.commit()
            return True
        except Error as e:
            print(f"Error ending week: {e}")
            return False
        finally:
            conn.close()
    return False

def get_recent_league_bets(league_id, limit=5):
    """Get the most recent unique fixture bets made by users in a league for league.html"""
    conn = get_db_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            # Fget all unique match_ids with their latest bet time
            c.execute('''
                SELECT match_id, MAX(created_at) as latest_bet_time
                FROM user_predictions
                WHERE league_id = ?
                GROUP BY match_id
                ORDER BY latest_bet_time DESC
                LIMIT ?
            ''', (league_id, limit))
            
            matches = c.fetchall()
            
            # For each match, get the user who made the latest bet
            recent_bets = []
            for match in matches:
                match_id = match[0]
                c.execute('''
                    SELECT u.username, p.created_at, p.home_score, p.away_score
                    FROM user_predictions p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.match_id = ? AND p.league_id = ?
                    ORDER BY p.created_at DESC
                    LIMIT 1
                ''', (match_id, league_id))
                
                bet_info = c.fetchone()
                if bet_info:
                    recent_bets.append({
                        'match_id': match_id,
                        'username': bet_info[0],
                        'created_at': bet_info[1],
                        'home_score': bet_info[2],
                        'away_score': bet_info[3]
                    })
            
            return recent_bets
        except Error as e:
            print(f"Error getting recent league bets: {e}")
            return []
        finally:
            conn.close()
    return []