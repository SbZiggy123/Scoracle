from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from .models import get_user, add_user, user_exists, init_db, verify_password, add_fantasy_league, get_league_by_code, get_public_leagues, save_prediction, get_user_predictions, get_league_by_id, get_user_leagues, is_user_in_league, add_user_to_league
import aiohttp
from understat import Understat # https://github.com/amosbastian/understat
import json

main = Blueprint('main', __name__)
    
    # Initialize database before the first request
@main.before_app_request
def initialise_database():
    init_db()
    
    
@main.route('/')
def mainpage():
    return render_template("base.html")

@main.route('/PremierLeague')
async def premier_league():
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        # Gets league table without headers cos I put them in already in html.
        table = await understat.get_league_table("epl", 2024, with_headers=False)
        
        results = await understat.get_league_results("epl", 2024)
        recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
            
        fixtures = await understat.get_league_fixtures("epl", 2024)
        upcoming_fixtures = sorted(fixtures, key=lambda x: x["datetime"])[:5]
        # lambda gets datetime... in docs
        
        return render_template("PremierLeague.html", 
                               table=table,
                               recent_results=recent_results,
                               upcoming_fixtures=upcoming_fixtures)


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
def league(league_id):
    league = get_league_by_id(league_id)
    if not league:
        flash("League not found")
        return redirect(url_for("main.join_league"))

    members_str = league.get("members")
    if members_str:
        member_list = [x.strip() for x in members_str.split(",") if x.strip()]
    else:
        member_list = []
    league["member_list"] = member_list

    return render_template("league.html", league=league)


@main.route('/myLeagues')
def my_leagues():
    if "username" not in session:
        flash("You must be logged in to view your leagues!")
        return redirect(url_for("main.login"))

    username = session["username"]
    user_leagues = get_user_leagues(username)

    return render_template("myLeagues.html", leagues=user_leagues)



@main.route('/fixtures')
@main.route("/fixtures/<team_name>")
async def fixtures(team_name=None):
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        if team_name:
            results = await understat.get_team_results(team_name, 2024)
            recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
            
            fixtures = await understat.get_team_fixtures(team_name, 2024)
            upcoming_fixtures = sorted(fixtures, key=lambda x: x["datetime"])[:5]
            return render_template(
                "fixtures.html",
                team_name=team_name,
                recent_results=recent_results,
                upcoming_fixtures=upcoming_fixtures
            )
        return render_template("fixtures.html")

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

@main.route('/prediction/<match_id>', methods=['GET', 'POST'])
async def prediction(match_id):
    # Debug the match_id parameter
    print(f"DEBUG: match_id type: {type(match_id)}, value: {match_id}")
    
    form = PredictionForm()
    # Create a prediction system instance
    prediction_system = PredictionSystem()
    
    try:
        prediction_data = await prediction_system.predict_match(match_id, 2024)
        print(f"DEBUG: Got prediction data: {bool(prediction_data)}")
    except Exception as e:
        import traceback
        print(f"ERROR getting prediction data: {e}")
        print(traceback.format_exc())
        flash("Error retrieving match data", "error")
        return redirect(url_for("main.fixtures"))
    
    if not prediction_data:
        flash("Match not found", "error")
        return redirect(url_for("main.fixtures"))
        
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
            
            print(f"DEBUG: Prediction details - User ID: {user['id']}, Match ID: {match_id}")
            print(f"DEBUG: Home score: {home_score}, Away score: {away_score}")
            
            home_expected = prediction_data["home_expected"]
            away_expected = prediction_data["away_expected"]
        
            points_data = prediction_system.calculate_points(
                home_expected,
                away_expected,
                [home_score, away_score]
            )
            
            print(f"DEBUG: Points data: {points_data}")
            
            # Convert match_id to string if it's not already
            match_id_str = str(match_id)
            
            save_result = save_prediction(
                user["id"], match_id_str, home_score, away_score, 
                multiplier=points_data["multiplier"], 
                potential_exact_points=points_data["exact_score"],
                potential_result_points=points_data["correct_result"]
            )
            
            print(f"DEBUG: Save prediction result: {save_result}")
            
            if save_result:
                flash("Your prediction has been saved!", "success")
                if 'view_all_bets' in request.form:
                    return redirect(url_for("main.yourBets"))
            else:
                flash("Failed to save your prediction. Please try again.", "danger")
                
        except Exception as e:
            import traceback
            print(f"ERROR in prediction submission: {e}")
            print(traceback.format_exc())
            flash("An error occurred while saving your prediction", "danger")
                
    return render_template(
        "prediction.html",
        form=form,
        match=prediction_data['match'],
        home_xg=prediction_data['home_xg'],
        away_xg=prediction_data['away_xg'],
        ai_prediction=prediction_data['prediction'],
        probabilities=prediction_data['probabilities'],
        home_xg_performance=prediction_data['home_xg_performance'],
        away_xg_performance=prediction_data['away_xg_performance'],
        home_opposition=prediction_data['home_opposition'],
        away_opposition=prediction_data['away_opposition'],
        home_expected=prediction_data['home_expected'],
        away_expected=prediction_data['away_expected'],
        league_positions=await prediction_system.get_league_positions(2024),
        user_prediction=user_prediction
    )

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
    
    # Fetch match details for each prediction
    match_details = {}
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        fixtures = await understat.get_league_fixtures("epl", 2024)
        results = await understat.get_league_results("epl", 2024)
        
        all_matches = fixtures + results
        
        for match in all_matches:
            match_details[match["id"]] = {
                "home_team": match["h"]["title"],
                "away_team": match["a"]["title"],
                "datetime": match["datetime"]
            }
    
    return render_template("yourBets.html", predictions=predictions, match_details=match_details)





@main.route("/result/<match_id>") #named differently to the html page it's using btw
async def single_result(match_id):
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        results = await understat.get_league_results("epl", 2024)
        match = next((result for result in results if result["id"] == match_id), None)
        
        if match:
            match_players = await understat.get_match_players(match_id)
            match_shots = await understat.get_match_shots(match_id)

            # for table popup gonna do
            
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
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                match_shots=match_shots
            )
        else:
            flash("Match not found", "error")
            return redirect(url_for("main.fixtures")) # should this be premleague... maybe 
        

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

        user = get_user(username)  # Fetch user from database.. redundant?

        if user and verify_password(username, password):
            session["username"] = username  # Store user session
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

@main.route("/home")
def home():
    '''Inprogress'''
    if "username" not in session:
        return redirect(url_for("main.login"))
    else:
        user = get_user(session["username"])
        totalLeagues = len(get_user_leagues(user))
        teams = Understat.get_teams("epl", 2024)
        team_names = []
        for team in teams:
            team_name = team["title"]
            team_names.append(team_name)
    return render_template("home.html", totalLeagues=totalLeagues, username=session["username"], team_names=team_names)
