from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from .models import get_user, add_user, user_exists, init_db, verify_password, add_fantasy_league, get_league_by_code, get_public_leagues
from .predict import predictxG
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
    if request.method == "POST":
        league_name = request.form.get("league_name")
        league_type = request.form.get("league_type")
        privacy = request.form.get("privacy")

        if not league_name or not league_type or not privacy:
            flash("All fields are required!", "danger")
            return redirect(url_for("main.create_league"))
        
        success = add_fantasy_league(league_name, league_type, privacy)
        
        if success:
            if privacy == "Private":
                flash(f"League '{league_name}' created successfully! Your private code: {success}", "success")
            else:
                flash(f"League '{league_name}' created successfully!", "success")
        else:
            flash("Error creating league. Please try again.", "danger")

        return redirect(url_for("main.create_league"))

    return render_template("createLeague.html")

@main.route('/myLeagues')
def my_leagues():
    return render_template("myLeagues.html")

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


from .prediction_model import PredictionSystem

@main.route('/prediction/<match_id>', methods=['GET', 'POST'])
async def prediction(match_id):
    # Create a prediction system instance
    prediction_system = PredictionSystem()
    prediction_data = await prediction_system.predict_match(match_id, 2024)
    if not prediction_data:
        flash("Match not found", "error")
        return redirect(url_for("main.fixtures"))
        
        
    # if request.method == 'POST' etc....

    return render_template(
        "prediction.html",
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
        league_positions=await prediction_system.get_league_positions(2024)
    )
        


# Stats of users predictions in bottom of page
        
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
        

@main.route('/joinLeague', methods=['GET', 'POST'])
def join_league():
    if request.method == "POST":
        league_code = request.form.get("league_code")

        # Check if the league exists by its code
        league = get_league_by_code(league_code)

        if league:
            flash(f"Joined private league: {league['league_name']}!", "success")
        else:
            flash("Invalid league code!", "danger")

        return redirect(url_for("main.join_league"))

    # Get list of public leagues
    public_leagues = get_public_leagues()

    return render_template("joinLeague.html", leagues=public_leagues)

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
    if "username" not in session:
        return redirect(url_for("main.login"))
    return render_template("home.html", username=session["username"])
