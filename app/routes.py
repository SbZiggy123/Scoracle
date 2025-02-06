
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from .models import get_user, add_user, user_exists, init_db, verify_password

main = Blueprint('main', __name__)

@main.before_app_first_request
def initialise_database():
    init_db()
    
    
@main.route('/')
def mainpage():
    return render_template("base.html")

@main.route('/PremierLeague')
def premier_league():
    return render_template("PremierLeague.html")

@main.route('/createLeague')
def create_league():
    return render_template("createLeague.html")

@main.route('/currentLeagues')
def current_leagues():
    return render_template("currentLeagues.html")

@main.route('/fixtures')
def fixtures():
    return render_template("fixtures.html")

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

        user = get_user(username)  # Fetch user from database

        if verify_password(username, password):
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