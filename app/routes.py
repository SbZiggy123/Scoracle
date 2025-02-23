from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from .models import get_user, add_user, user_exists, init_db, verify_password
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

@main.route('/createLeague')
def create_league():
    return render_template("createLeague.html")

@main.route('/currentLeagues')
def current_leagues():
    return render_template("currentLeagues.html")

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
    
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        # Get match details
        fixtures = await understat.get_league_fixtures("epl", 2024)
        match = next((fixture for fixture in fixtures if fixture["id"] == match_id), None)
        
        # Switched to initial test here easier to read
        if not match:
            flash("Match not found", "error")
            return redirect(url_for("main.fixtures"))
        
        """could move this to model later"""
        # Get recent xG data for both teams directly from Understat
        home_xg = await prediction_system.get_team_recent_data(match["h"]["title"], 2024)
        away_xg = await prediction_system.get_team_recent_data(match["a"]["title"], 2024)
        
        # Generate AI prediction
        ai_home, ai_away = prediction_system.predict_score(home_xg, away_xg)
        
        # Calculate probabilities
        probabilities = prediction_system.calculate_probabilities(
            prediction_system.calculate_expected_score(home_xg) * prediction_system.home_weight,
            prediction_system.calculate_expected_score(away_xg)
        )
        

        return render_template(
            "prediction.html",
            match=match,
            home_xg=home_xg,
            away_xg=away_xg,
            ai_prediction={
                "home": ai_home,
                "away": ai_away
            },
            probabilities=probabilities
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
            team_crests = { 
                "Arsenal": "/static/Arsenal.png",
                "Aston Villa": "/static/AstonVila.png",
                "Bournemouth": "/static/Bournemouth.png",
                "Brentford": "/static/Brentford.png",
                "Brighton": "/static/Brighton.png",
                "Chelsea": "/static/Chelsea.png",
                "Manchester City": "/static/City.png",
                "Manchester United": "/static/United.png",
                "Everton": "/static/City.png",
                "Fulham": "/static/Fulham.png",
                "Ipswich": "/static/Ipswich.png",
                "Leicester": "/static/Leicester.png",
                "Liverpool": "/static/Liverpool.png",
                "Newcastle": "/static/Newcastle.png",
                "Crystal Palace": "/static/Palace.png",
                "Southampton": "/static/Southampton.png",
                "Tottenham Hotspurs": "/static/Spurs.png",
                "West Ham": "/static/WestHam.png",
                "Wolverhampton Wanderers": "/static/Wolves.png",

            }
            
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
        

@main.route('/joinLeague')
def join_league():
    return render_template("joinLeague.html")

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
