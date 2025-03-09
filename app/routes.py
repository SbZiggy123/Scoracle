import os
import uuid
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from werkzeug.utils import secure_filename
from .models import get_user, update_user, add_user, user_exists, init_db, verify_password, add_fantasy_league, get_league_by_code, get_public_leagues, save_prediction, get_user_predictions, get_league_by_id, get_user_leagues, is_user_in_league, add_user_to_league, get_league_leaderboard, place_bet, get_profile_pic, get_db_connection, get_user_player_predictions, save_player_prediction, ensure_user_in_global_league, get_seasonal_league_leaderboard, get_recent_league_bets
from .player_prediction_model import PlayerPredictionSystem
import aiohttp
from understat import Understat # https://github.com/amosbastian/understat
import json
from datetime import datetime

main = Blueprint('main', __name__)
app = Flask(__name__)

LEAGUE_MAPPING = {
    "epl": "Premier League",
    "La_liga": "La Liga",
    "Bundesliga": "Bundesliga", 
    "Serie_A": "Serie A",
    "Ligue_1": "Ligue 1"
}

LEAGUE_ICONS = {
    "epl": "PremLogo.png",
    "La_liga": "LaLigaLogo.png",
    "Bundesliga": "BundesligaLogo.png",
    "Serie_A": "SerieALogo.png", 
    "Ligue_1": "Ligue1Logo.png"
}

DEFAULT_LEAGUE = "epl"

UPLOAD_FOLDER = 'app/static/profilepics/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


    # Initialize database before the first request
@main.before_app_request
def initialise_database():
    init_db()
    
    
@main.route('/')
async def homepage():
    for league_code in LEAGUE_MAPPING:
        league_name = LEAGUE_MAPPING[league_code]
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            table = await understat.get_league_table(league_code, 2024, with_headers=False)
            results = await understat.get_league_results(league_code, 2024)
            recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
            fixtures = await understat.get_league_fixtures(league_code, 2024)
            upcoming_fixtures = sorted(fixtures, key=lambda x: x["datetime"])[:5]
            return render_template("main.html",  # change it if you want. dont bother
                            league_name=league_name,
                            league_code=league_code,
                            table=table,
                            recent_results=recent_results,
                            upcoming_fixtures=upcoming_fixtures)


@main.route('/league/<league_code>')
@main.route('/league')  # Deafault to prem
async def league_view(league_code=DEFAULT_LEAGUE):
    # Just to make sure it's in mapping above
    if league_code not in LEAGUE_MAPPING:
        league_code = DEFAULT_LEAGUE
    league_name = LEAGUE_MAPPING[league_code]
    
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        table = await understat.get_league_table(league_code, 2024, with_headers=False)
        
        results = await understat.get_league_results(league_code, 2024)
        recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
        
        fixtures = await understat.get_league_fixtures(league_code, 2024)
        upcoming_fixtures = sorted(fixtures, key=lambda x: x["datetime"])[:5]
    
        return render_template("PremierLeague.html",  # change it if you want. dont bother
                        league_name=league_name,
                        league_code=league_code,
                        table=table,
                        recent_results=recent_results,
                        upcoming_fixtures=upcoming_fixtures)
# if anything leaking around:
@main.route('/PremierLeague')
def premier_league_redirect():
    return redirect(url_for('main.league_view', league_code="epl"))




@main.route('/createLeague', methods=["GET", "POST"])
def create_league():
    if "username" not in session:
        flash("You must be logged in to create a league")
        return redirect(url_for("main.login"))

    if request.method == "POST":
        league_name = request.form.get("league_name")
        league_type = request.form.get("league_type")
        privacy = request.form.get("privacy")
        username = session["username"]

        if not league_name or not league_type or not privacy:
            flash("All fields are required")
            return redirect(url_for("main.create_league"))

        success = add_fantasy_league(league_name, league_type, privacy, username)

        if success:
            if privacy == "Private":
                flash(f"League '{league_name}' created successfully! Your private code: {success}")
            else:
                flash(f"League '{league_name}' created successfully")
        else:
            flash("Error creating league. Please try again.", "danger")

        return redirect(url_for("main.create_league"))

    return render_template("createLeague.html")

#route to reset season on seasonal league. resetting timer and points, and awarding top player with trophy
@main.route("/endSeason/<int:league_id>", methods=["POST"])
def end_season(league_id):
    league = get_league_by_id(league_id)
    if not league:
        flash("League not found.", "danger")
        return redirect(url_for("main.home"))

    if league.get("league_type") != "seasonal":
        flash("This league is not a seasonal league!", "danger")
        return redirect(url_for("main.league", league_id=league_id))
    
    from .models import end_seasonal_round
    success = end_seasonal_round(league_id)
    if success:
        flash("Season ended! Trophies awarded and scores reset.", "success")
    else:
        flash("Error ending the season.", "danger")

    return redirect(url_for("main.league", league_id=league_id))


@main.route("/joinLeague", methods=["GET", "POST"])
def join_league():
    if "username" not in session:
        flash("You must be logged in to join a league")
        return redirect(url_for("main.login"))

    username = session["username"]

    if request.method == "POST":
        league_code = request.form.get("league_code")
        league = get_league_by_code(league_code)

        if league:
            league_id = league["id"]

            if is_user_in_league(username, league_id):
                flash("You are already a member of this league")
            else:
                if add_user_to_league(username, league_id):
                    flash(f"Successfully joined private league: {league['league_name']}", "success")
                else:
                    flash("Error joining league. Try again")
        else:
            flash("Invalid league code")

        return redirect(url_for("main.join_league"))

    public_leagues = get_public_leagues()
    user_leagues_list = get_user_leagues(username)
    user_league_ids = [str(league['id']) for league in user_leagues_list]

    return render_template("joinLeague.html", leagues=public_leagues, user_leagues=user_league_ids)


#called when user presses the join button on public league
@main.route("/joinPublicLeague/<int:league_id>", methods=["POST"])
def join_public_league(league_id):
    if "username" not in session:
        flash("You must be logged in to join a league")
        return redirect(url_for("main.login"))

    username = session["username"]
    league = get_league_by_id(league_id)

    if league:
        if is_user_in_league(username, league_id):
            flash("You are already a member of this league")
        else:
            if add_user_to_league(username, league_id):
                flash(f"Successfully joined league: {league['league_name']}")
            else:
                flash("Error joining league")
    else:
        flash("League not found")

    return redirect(url_for("main.join_league"))



#called when user clicks on league name
@main.route("/league/<int:league_id>")
async def league(league_id):
    league = get_league_by_id(league_id)
    if not league:
        flash("League not found")
        return redirect(url_for("main.join_league"))

    league_type = league.get("league_type")
    members_str = league.get("members", "")
    member_list = [x.strip() for x in members_str.split(",") if x.strip()] if members_str else []
    league["member_list"] = member_list

    if league_type == "classic":
        league["leaderboard"] = get_league_leaderboard(league_id)
    elif league_type == "seasonal":
        league["leaderboard"] = get_seasonal_league_leaderboard(league_id)

        if league.get("season_end"):
            season_end_str = league["season_end"]
            try:
                season_end_dt = datetime.strptime(season_end_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                season_end_dt = None

            if season_end_dt:
                diff = season_end_dt - datetime.now()
                time_left = int(diff.total_seconds())
                if time_left < 0:
                    time_left = 0
                league["time_left"] = time_left
            else:
                league["time_left"] = 0
        else:
            league["time_left"] = 0

    else:
        flash("error creating league leaderboard")
    
    recent_bets = []
    recent_bets_info = get_recent_league_bets(league_id)
        
    # Get match details for these bets
    match_details = {}
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        fixtures = await understat.get_league_fixtures("epl", 2024)
        results = await understat.get_league_results("epl", 2024)
            
        all_matches = fixtures + results
            
        # Get fixture IDs ezier
        fixture_ids = [f["id"] for f in fixtures]
            
        for match in all_matches:
            match_id = match["id"]
            match_details[match_id] = match
            
        # Combine bet info with match details
    for bet in recent_bets_info:
        match_id = bet['match_id']
        if match_id in match_details:
            match = match_details[match_id]
            # match still a fixture
            if match_id in fixture_ids:
                bet['match'] = match
                recent_bets.append(bet)

    return render_template("league.html", league=league, recent_bets=recent_bets)

@main.route('/place_bet', methods=['POST'])
def place_bet_route():
    if "username" not in session:
        return jsonify({"success": False, "message": "You must be logged in to bet"}), 403

    user = get_user(session["username"])
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    data = request.json
    league_id = data.get("league_id")
    match_id = data.get("match_id")
    bet_amount = data.get("bet_amount")
    prediction = data.get("prediction")

    if not all([league_id, match_id, bet_amount, prediction]):
        return jsonify({"success": False, "message": "Missing data"}), 400

    result = place_bet(user["id"], league_id, match_id, bet_amount, prediction)
    return jsonify(result)


@main.route("/league_update", methods=["GET"])
async def league_update():
    if "username" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 403

    league_id = request.args.get("league_id")
    match_id = request.args.get("match_id")
    
    if not league_id or not match_id:
        return jsonify({"success": False, "message": "Missing parameters"}), 400

    async with aiohttp.ClientSession() as session_obj:
        understat = Understat(session_obj)
        results = await understat.get_league_results("epl", 2024)
        match = next((result for result in results if result["id"] == match_id), None)
        
        if match:
            home_goals = match["goals"]["h"]
            away_goals = match["goals"]["a"]
            from .models import process_match_bets
            process_match_bets(match_id, home_goals, away_goals)
            
    from .models import get_league_leaderboard
    updated_leaderboard = get_league_leaderboard(league_id)
    return jsonify({"success": True, "leaderboard": updated_leaderboard})


@main.route('/myLeagues')
def my_leagues():
    if "username" not in session:
        flash("You must be logged in to view your leagues!")
        return redirect(url_for("main.login"))

    username = session["username"]
    user_leagues = get_user_leagues(username)

    return render_template("myLeagues.html", leagues=user_leagues)



@main.route('/fixtures/<league_code>/<team_name>')
@main.route('/fixtures/<league_code>')
@main.route('/fixtures')  # Default route kinda fkced cos does nil
async def fixtures(league_code=DEFAULT_LEAGUE, team_name=None):
    # Validate league_code
    if league_code not in LEAGUE_MAPPING:
        league_code = DEFAULT_LEAGUE
    
    league_name = LEAGUE_MAPPING[league_code]
    
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        if team_name:
            results = await understat.get_team_results(team_name, 2024)
            recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
            
            fixtures = await understat.get_team_fixtures(team_name, 2024)
            upcoming_fixtures = sorted(fixtures, key=lambda x: x["datetime"])[:5]
            return render_template(
                "fixtures.html",
                league_code=league_code,
                league_name=league_name,
                team_name=team_name,
                recent_results=recent_results,
                upcoming_fixtures=upcoming_fixtures
            )
        return render_template("fixtures.html", 
                              league_code=league_code, 
                              league_name=league_name)

class PredictionForm(FlaskForm):
    home_score = IntegerField('Home Score', validators=[
        DataRequired(),
        NumberRange(min=0, max=20, message="Score must be between 0 and 20")
    ])
    away_score = IntegerField('Away Score', validators=[
        DataRequired(), 
        NumberRange(min=0, max=20, message="Score must be between 0 and 20")
    ])
    submit = SubmitField('Save Prediction')

from .prediction_model import PredictionSystem

@main.route('/prediction/<league_code>/<match_id>', methods=['GET', 'POST'])
@main.route('/prediction/<match_id>', methods=['GET', 'POST'])
async def prediction(match_id, league_code=DEFAULT_LEAGUE):
    # Debug the match_id parameter
    print(f"DEBUG: match_id type: {type(match_id)}, value: {match_id}")
    
    if league_code not in LEAGUE_MAPPING:
        league_code = DEFAULT_LEAGUE
        
    form = PredictionForm()
    # Create a prediction system instance
    prediction_system = PredictionSystem()
    player_prediction_system = PlayerPredictionSystem()
   
    
    try:
        # Get player prediction data
        player_data = await player_prediction_system.get_likely_match_players(match_id, league_code, 2024)
        
        # Process player data for template
        home_players = []
        away_players = []
        
        if player_data:
            # Calculate expected stats for each player
            for player in player_data["home_players"]:
                expected_stats = player_prediction_system.calculate_player_expected_stats(player)
                player["expected_stats"] = expected_stats
                home_players.append(player)
                
            for player in player_data["away_players"]:
                expected_stats = player_prediction_system.calculate_player_expected_stats(player)
                player["expected_stats"] = expected_stats
                away_players.append(player)
            
        # Get user's existing player predictions if logged in
        user_player_predictions = {}
        if "username" in session:
            user = get_user(session["username"])
            if user:
                predictions = get_user_player_predictions(user["id"], match_id)
                for pred in predictions:
                    user_player_predictions[pred["player_id"]] = pred
    except Exception as e:
        import traceback
        print(f"Error getting player prediction data: {e}")
        print(traceback.format_exc())
        home_players = []
        away_players = []
        user_player_predictions = {}
    
    # Get user's leagues so they can decide what league they wanna predict in 
    user_leagues = []
    if "username" in session:
        user = get_user(session["username"])
        if user:
            user_leagues = get_user_leagues(session["username"])
    
    try:
        prediction_data = await prediction_system.predict_match(match_id, league_code, 2024)
        print(f"DEBUG: Got prediction data: {bool(prediction_data)}")
        for key in ["home_xg", "away_xg", "home_goals", "away_goals", 
                   "home_opponents", "away_opponents", "home_dates", 
                   "away_dates", "home_results", "away_results"]:
            if key in prediction_data:
                prediction_data[key] = list(reversed(prediction_data[key]))
    except Exception as e:
        import traceback
        print(f"ERROR getting prediction data: {e}")
        print(traceback.format_exc())
        flash("Error retrieving match data", "error")
        return redirect(url_for("main.fixtures", league_code=league_code))
    
    if not prediction_data:
        flash("Match not found", "error")
        return redirect(url_for("main.fixtures", league_code=league_code))
        
    user_prediction = None
    
    if "username" in session:
        print(f"DEBUG: User in session: {session['username']}")
        user = get_user(session["username"])
        if user:
            print(f"DEBUG: User ID: {user['id']}")
            user_predictions = get_user_predictions(user["id"])
            print(f"DEBUG: Found {len(user_predictions)} existing predictions")
            for pred in user_predictions:
                if pred["match_id"] == match_id:
                    print(f"DEBUG: Found existing prediction for this match")
                    user_prediction = {"home_score": pred["home_score"], "away_score": pred["away_score"]}

                    if not form.home_score.data:
                        form.home_score.data = pred["home_score"]
                    if not form.away_score.data:
                        form.away_score.data = pred["away_score"]
                    break
    
    # Handle form  
    if "username" in session and request.method == "POST":
        print(f"DEBUG: Form validation: {form.validate_on_submit()}")
        if not form.validate_on_submit():
            print(f"DEBUG: Form validation errors: {form.errors}")
            
    if "username" in session and form.validate_on_submit():
        try:
            user = get_user(session["username"])
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("main.home"))
            
            home_score = form.home_score.data
            away_score = form.away_score.data
            league_id = request.form.get('league_id', '1')  # Default to global league if not specified
            bet_amount = request.form.get('bet_amount', '50')  # Default bet amount
            
            try:
                league_id = int(league_id)
                bet_amount = int(bet_amount)
            except ValueError:
                flash("Invalid league or bet amount.", "danger")
                return redirect(url_for("main.prediction", league_code=league_code, match_id=match_id))
            
            # Validate bet amount
            if bet_amount < 10 or bet_amount > 500:
                flash("Bet amount must be between 10 and 500.", "danger")
                return redirect(url_for("main.prediction", league_code=league_code, match_id=match_id))
            
            # Check if user has enough points in the league
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = ?", (user["id"], league_id))
            league_score = c.fetchone()
            
            if not league_score or league_score[0] < bet_amount:
                flash(f"Insufficient points to place a bet of {bet_amount}.", "danger")
                return redirect(url_for("main.prediction", league_code=league_code, match_id=match_id))
                
            # Deduct bet amount
            new_score = league_score[0] - bet_amount
            c.execute("UPDATE league_scores SET score = ? WHERE user_id = ? AND league_id = ?", 
                      (new_score, user["id"], league_id))
            conn.commit()
            
            # Also deduct from global league if this is not the global league
            # Bet ALWAYS deducted from global league
            if league_id != 1:
                c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = 1", (user["id"],))
                global_score = c.fetchone()
                if global_score and global_score[0] >= bet_amount:
                    new_global_score = global_score[0] - bet_amount
                    c.execute("UPDATE league_scores SET score = ? WHERE user_id = ? AND league_id = 1", 
                              (new_global_score, user["id"]))
                    conn.commit()
            
         
            print(f"DEBUG: Prediction details - User ID: {user['id']}, Match ID: {match_id}")
            print(f"DEBUG: Home score: {home_score}, Away score: {away_score}")
            print(f"DEBUG: League ID: {league_id}, Bet Amount: {bet_amount}")
            
            home_expected = prediction_data["home_expected"]
            away_expected = prediction_data["away_expected"]
        
            points_data = prediction_system.calculate_points(
                home_expected,
                away_expected,
                [home_score, away_score],
                bet_amount  
            )
            
            print(f"DEBUG: Points data: {points_data}")
            
            # Convert match_id to string if it's not already
            match_id_str = str(match_id)
            
            # Check if prediction already exists
            c.execute("SELECT id FROM user_predictions WHERE user_id = ? AND match_id = ? AND league_id = ?", 
                     (user["id"], match_id_str, league_id))
            existing = c.fetchone()
            
            if existing:
                # Update existing prediction
                c.execute('''
                    UPDATE user_predictions 
                    SET home_score = ?, away_score = ?, bet_amount = ?, 
                        multiplier = ?, potential_exact_points = ?, potential_result_points = ?, 
                        created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (home_score, away_score, bet_amount, 
                      points_data["multiplier"], points_data["exact_score"], points_data["correct_result"], 
                      existing[0]))
            else:
                # Insert new prediction
                c.execute('''
                    INSERT INTO user_predictions
                    (user_id, match_id, home_score, away_score, bet_amount, 
                     multiplier, potential_exact_points, potential_result_points, league_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user["id"], match_id_str, home_score, away_score, bet_amount, 
                      points_data["multiplier"], points_data["exact_score"], points_data["correct_result"], 
                      league_id))
            
            conn.commit()
            conn.close()
            
            # Also save to global league if this is not the global league
            if league_id != 1:
                save_to_global = save_prediction(
                    user["id"], match_id_str, home_score, away_score, bet_amount, None,
                    multiplier=points_data["multiplier"], 
                    potential_exact_points=points_data["exact_score"],
                    potential_result_points=points_data["correct_result"],
                    league_id=1
                )
                if not save_to_global:
                    print("WARNING: Failed to save prediction to global league")
            
            user_prediction = {"home_score": home_score, "away_score": away_score}
            flash("Your prediction has been saved!", "success")
            if 'view_all_bets' in request.form:
                return redirect(url_for("main.yourBets"))
        except Exception as e:
            import traceback
            print(f"ERROR in prediction submission: {e}")
            print(traceback.format_exc())
            flash("An error occurred while saving your prediction", "danger")
        
    return render_template(
        "prediction.html",
        league_code=league_code,
        league_name=LEAGUE_MAPPING[league_code],
        form=form,
        match=prediction_data['match'],
        home_xg=prediction_data['home_xg'],
        away_xg=prediction_data['away_xg'],
        home_goals=prediction_data['home_goals'],
        away_goals=prediction_data['away_goals'],
        home_opponents=prediction_data['home_opponents'],
        away_opponents=prediction_data['away_opponents'],
        home_dates=prediction_data['home_dates'],
        away_dates=prediction_data['away_dates'],
        home_results=prediction_data['home_results'],
        away_results=prediction_data['away_results'],
        ai_prediction=prediction_data['prediction'],
        probabilities=prediction_data['probabilities'],
        home_xg_performance=prediction_data['home_xg_performance'],
        away_xg_performance=prediction_data['away_xg_performance'],
        home_expected=prediction_data['home_expected'],
        away_expected=prediction_data['away_expected'],
        league_positions=await prediction_system.get_league_positions(league_code, 2024),
        home_weight=prediction_system.home_weight, 
        user_prediction=user_prediction,
        home_players=home_players,
        away_players=away_players,
        user_player_predictions=user_player_predictions,
        user_leagues=user_leagues
    )
    
#need endpoints
@main.route('/api/player-predictions/<league_code>/<match_id>', methods=['GET'])
@main.route('/api/player-predictions/<match_id>', methods=['GET'])
async def get_player_predictions(match_id, league_code=DEFAULT_LEAGUE):
    """Get likely players for a match and their stats"""
    if league_code not in LEAGUE_MAPPING:
        league_code = DEFAULT_LEAGUE
    player_prediction_system = PlayerPredictionSystem()
    
    try:
        player_data = await player_prediction_system.get_likely_match_players(match_id, league_code, 2024)
        
        if not player_data:
            return jsonify({"error": "Match not found"})
            
        # Expected stats
        for team in ["home_players", "away_players"]:
            for i, player in enumerate(player_data[team]):
                expected_stats = player_prediction_system.calculate_player_expected_stats(player)
                player_data[team][i]["expected_stats"] = expected_stats
        
        if "username" in session:
            user = get_user(session["username"])
            if user:
                predictions = get_user_player_predictions(user["id"], match_id)
                player_data["user_predictions"] = predictions
        
        return jsonify(player_data)
    # Error
    except Exception as e:
        import traceback
        print(f"Error getting player predictions: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)})
    
@main.route('/api/player-predictions/<league_code>/<match_id>', methods=['POST'])
@main.route('/api/player-predictions/<match_id>', methods=['POST'])
async def save_player_predictions(match_id, league_code=DEFAULT_LEAGUE):
    """Save a user's player predictions with league integration"""
    if league_code not in LEAGUE_MAPPING:
        league_code = DEFAULT_LEAGUE
    
    if "username" not in session:
        return jsonify({"error": "You must be logged in to make predictions"})
    
    user = get_user(session["username"])
    if not user:
        return jsonify({"error": "User not found"})
    
    # Get prediction data from request
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Invalid prediction data"})
    
    player_prediction_system = PlayerPredictionSystem()
    conn = get_db_connection()
    
    # Get player data to calculate multipliers
    player_data = await player_prediction_system.get_likely_match_players(match_id, league_code, 2024)
    
    # Create a map of player IDs to their data as a dict
    player_dict = {}
    for team in ["home_players", "away_players"]:
        for player in player_data[team]:
            player_dict[player["id"]] = player
    
    results = []
    
    try:
        c = conn.cursor()
        
        for prediction in data:
            player_id = prediction.get("player_id")
            goals = prediction.get("goals", 0)
            shots = prediction.get("shots", 0)
            league_id = prediction.get("league_id", 1)  # Default to global league
            bet_amount = prediction.get("bet_amount", 50)  # Default bet amount
            
            # Validate bet amount
            if bet_amount < 10 or bet_amount > 500:
                results.append({
                    "player_id": player_id,
                    "success": False,
                    "message": "Bet amount must be between 10 and 500"
                })
                continue
            
            if not player_id or player_id not in player_dict:
                results.append({
                    "player_id": player_id,
                    "success": False,
                    "message": "Player not found"
                })
                continue
            
            # Check if user has enough points in the league
            c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = ?", 
                     (user["id"], league_id))
            league_score = c.fetchone()
            
            if not league_score or league_score[0] < bet_amount:
                results.append({
                    "player_id": player_id,
                    "success": False,
                    "message": f"Insufficient points to place a bet of {bet_amount}"
                })
                continue
            
            # Deduct bet amount from league score
            new_score = league_score[0] - bet_amount
            c.execute("UPDATE league_scores SET score = ? WHERE user_id = ? AND league_id = ?", 
                     (new_score, user["id"], league_id))
            
            # Also deduct from global league if this is not the global league
            if int(league_id) != 1:
                c.execute("SELECT score FROM league_scores WHERE user_id = ? AND league_id = 1", (user["id"],))
                global_score = c.fetchone()
                if global_score and global_score[0] >= bet_amount:
                    new_global_score = global_score[0] - bet_amount
                    c.execute("UPDATE league_scores SET score = ? WHERE user_id = ? AND league_id = 1", 
                             (new_global_score, user["id"]))
            
            # Calculate points and multiplier (without minutes)
            player = player_dict[player_id]
            points_data = player_prediction_system.calculate_points(
                player, goals, shots
            )
            
            # Check if prediction already exists
            c.execute('''
                SELECT id FROM user_player_predictions 
                WHERE user_id = ? AND match_id = ? AND player_id = ? AND league_id = ?
            ''', (user["id"], match_id, player_id, league_id))
            existing = c.fetchone()
            
            if existing:
                # Update existing prediction
                c.execute('''
                    UPDATE user_player_predictions 
                    SET goals_prediction = ?, shots_prediction = ?, minutes_prediction = 0,
                        multiplier = ?, potential_points = ?, bet_amount = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (goals, shots, points_data["multiplier"], points_data["potential_points"], 
                      bet_amount, existing[0]))
            else:
                # Insert new prediction
                c.execute('''
                    INSERT INTO user_player_predictions
                    (user_id, match_id, player_id, goals_prediction, shots_prediction, 
                     minutes_prediction, multiplier, potential_points, league_id, bet_amount)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                ''', (user["id"], match_id, player_id, goals, shots, 
                     points_data["multiplier"], points_data["potential_points"], league_id, bet_amount))
            
            # Also save to global league if this is not the global league
            if int(league_id) != 1:
                # Check if prediction already exists in global league
                c.execute('''
                    SELECT id FROM user_player_predictions 
                    WHERE user_id = ? AND match_id = ? AND player_id = ? AND league_id = 1
                ''', (user["id"], match_id, player_id))
                global_existing = c.fetchone()
                
                if global_existing:
                    # Update existing prediction in global league
                    c.execute('''
                        UPDATE user_player_predictions 
                        SET goals_prediction = ?, shots_prediction = ?, minutes_prediction = 0,
                            multiplier = ?, potential_points = ?, bet_amount = ?, created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (goals, shots, points_data["multiplier"], points_data["potential_points"], 
                         bet_amount, global_existing[0]))
                else:
                    # Insert new prediction in global league
                    c.execute('''
                        INSERT INTO user_player_predictions
                        (user_id, match_id, player_id, goals_prediction, shots_prediction, 
                         minutes_prediction, multiplier, potential_points, league_id, bet_amount)
                        VALUES (?, ?, ?, ?, ?, 0, ?, ?, 1, ?)
                    ''', (user["id"], match_id, player_id, goals, shots, 
                         points_data["multiplier"], points_data["potential_points"], bet_amount))
            
            results.append({
                "player_id": player_id,
                "success": True,
                "multiplier": points_data["multiplier"],
                "potential_points": points_data["potential_points"]
            })
        
        conn.commit()
        
    except Exception as e:
        import traceback
        print(f"Error saving player predictions: {e}")
        print(traceback.format_exc())
        conn.rollback()
        return jsonify({"error": f"Error saving predictions: {str(e)}"})
    finally:
        conn.close()
    
    return jsonify({"results": results})

@main.route('/yourBets')
async def yourBets():
    from flask import session as flask_session
    if "username" not in flask_session:
        flash("You must be logged in to view your bets", "danger")
        return redirect(url_for("main.login"))
    
    user = get_user(flask_session["username"])
    if not user:
        flash("User not found", "danger")
        return redirect(url_for("main.home"))
    
    predictions = get_user_predictions(user["id"])
    player_predictions = get_user_player_predictions(user["id"])
    
    # Fetch leagues information for reference
    league_info = {}
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, league_name FROM fantasyLeagues")
    leagues = c.fetchall()
    conn.close()
    
    for league in leagues:
        league_info[league[0]] = league[1]
    
    # Fetch match details for each prediction
    match_details = {}
    player_details = {}
    
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        fixtures = await understat.get_league_fixtures("epl", 2024)
        results = await understat.get_league_results("epl", 2024)
        
        all_matches = fixtures + results
        
        for match in all_matches:
            match_id = match["id"]
            match_details[match_id] = {
                "home_team": match["h"]["title"],
                "away_team": match["a"]["title"],
                "datetime": match["datetime"]
            }
            
            # Get player details for matches with player predictions
            match_player_predictions = [p for p in player_predictions if p["match_id"] == match_id]
            if match_player_predictions:
                try:
                    match_players = await understat.get_match_players(match_id)
                    for team in ["h", "a"]:
                        if team in match_players:
                            for player_data in match_players[team].values():
                                player_details[player_data["player_id"]] = {
                                    "name": player_data["player"],
                                    "team": match[team]["title"]
                                }
                except Exception as e:
                    print(f"Error fetching player data for match {match_id}: {e}")
    
    return render_template("yourBets.html", 
                          predictions=predictions, 
                          player_predictions=player_predictions,
                          match_details=match_details,
                          player_details=player_details,
                          league_info=league_info)
# Stats of users predictions in bottom of page
        
@main.route("/result/<league_code>/<match_id>")
@main.route("/result/<match_id>") 
async def single_result(match_id, league_code=DEFAULT_LEAGUE):
    if league_code not in LEAGUE_MAPPING:
        league_code = DEFAULT_LEAGUE
    
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        results = await understat.get_league_results(league_code, 2024)
        match = next((result for result in results if result["id"] == match_id), None)
        
        if match:
            match_players = await understat.get_match_players(match_id)
            match_shots = await understat.get_match_shots(match_id)

            home_stats = {
                "shots": len(match_shots["h"]),
                "shots_on_target": len([shot for shot in match_shots["h"]
                                        if shot["result"] in ["SavedShot", "Goal"]]),
                "goals": match["goals"]["h"],
                "xG": float(match["xG"]["h"]),
                "player_stats": match_players["h"]
            }

            away_stats = {
                "shots": len(match_shots["a"]),
                "shots_on_target": len([shot for shot in match_shots["a"]
                                        if shot["result"] in ["SavedShot", "Goal"]]),
                "goals": match["goals"]["a"],
                "xG": float(match["xG"]["a"]),
                "player_stats": match_players["a"]
            }
                
            return render_template(
                "singleResult.html",
                league_code=league_code,
                league_name=LEAGUE_MAPPING[league_code],
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                match_shots=match_shots
            )
        else:
            flash("Match not found", "error")
            return redirect(url_for("main.fixtures", league_code=league_code))
        

# might not need this cos we have singleResult (takes match ID as param) 
# and also fixtures and results of a specific team in fixtures.html maybe rename to fixturesAndResults
@main.route('/results') 
def results():
    return render_template("results.html")


# WTForms Login Form
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

@main.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = get_user(username)  # Fetch user from database

        if user and verify_password(username, password):
            session["username"] = username  # Store user session
            
            # Ensure user is in global league
            ensure_user_in_global_league(user["id"], username)
            
            flash("Login successful!", "success")
            return redirect(url_for("main.home"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html", form=form)

# Logout Route
@main.route("/logout")
def logout():
    session.pop("username", None)
    flash("Logged out!", "info")
    return redirect(url_for("main.login"))

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    submit = SubmitField('Register')

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        password2 = form.password2.data

        if password != password2:
            flash("Passwords do not match!", "danger")
        elif user_exists(username):
            flash("Username already exists!", "danger")
        else:
            if add_user(username, password):
                # Get the newly created user
                user = get_user(username)
                
                # Add user to global league
                ensure_user_in_global_league(user["id"], username)
                
                flash("Registration successful! Please login.", "success")
                return redirect(url_for("main.login"))
            else:
                flash("Registration failed. Please try again.", "danger")

    return render_template('register.html', form=form)

@main.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')  # Get the search query from the URL parameters
    
    return render_template("results.html", query=query, results=results)

    return f" searched for: {query}"

@main.route("/home", methods=["GET", "POST"])
async def home():
    if "username" not in session:
        return redirect(url_for("main.login"))
    user = session["username"]

    form = UpdateForm()
    db = get_db_connection()
    if request.method == "POST":
        user = session["username"]
        new_username = request.form.get('username')
        favourite_team = request.form.get('favourite_team')
        if user != new_username:
            update_user(user, 'username', new_username)
            session["username"] = new_username
        update_user(user, 'favourite_team', favourite_team)

        profile_pic = request.files.get('profile_pic')
        if profile_pic:
            pic_filename = secure_filename(profile_pic.filename)
            pic_name = str(uuid.uuid1()) + "_" + pic_filename
            profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
            update_user(user, 'profile_pic', pic_name)

        db.commit()
        flash("User Updated Successfully!")
        return redirect(url_for("main.home")) 

    async with aiohttp.ClientSession() as understat_session:
        understat = Understat(understat_session)
        user = session["username"]
        totalLeagues = len(get_user_leagues(user))
        profile_pic = get_profile_pic(user)
        teams = await understat.get_teams("epl", 2024)
        form.favourite_team.choices = [(team['id'], team['title']) for team in teams]

    return render_template("home.html", leagues=totalLeagues, form=form, profile_pic=profile_pic, username=user)

class UpdateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    favourite_team = SelectField('Favortie Team', coerce=int, validate_choice=False)
    profile_pic = FileField('Change Profile Picture')
    update = SubmitField("Update")
