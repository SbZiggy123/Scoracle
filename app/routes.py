
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from .models import get_user, add_user, user_exists, init_db, verify_password
import aiohttp
from understat import Understat # https://github.com/amosbastian/understat

main = Blueprint('main', __name__)

@main.before_app_first_request
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

@main.route('/prediction/<match_id>')
async def prediction(match_id):
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        fixtures = await understat.get_league_fixtures("epl", 2024)
        match = next((fixture for fixture in fixtures if fixture["id"] == match_id))
        
        if match:
            return render_template(
                "prediction.html",
                match=match
            )
        else:
            flash("Match not found", "error")
            return redirect(url_for("main.fixtures"))

@main.route('/joinLeague')
def join_league():
    return render_template("joinLeague.html")

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
    return f" searched for: {query}"

@main.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("main.login"))
    return render_template("home.html", username=session["username"])