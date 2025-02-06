
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from .models import get_user, add_user, user_exists, init_db 

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


def get_user(username):
    #replace this with an actual query from the database
    fake_users = {"user1": "password123", "user2": "secret"}
    return {"username": username, "password": fake_users.get(username)} if username in fake_users else None

# WTForms Login Form
class LoginForm(FlaskForm):
    user_id = StringField("User ID", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

@main.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_id = form.user_id.data
        password = form.password.data

        user = get_user(user_id)  # Fetch user from database

        if user and user["password"] == password:
            session["user"] = user_id  # Store user session
            flash("Login successful!", "success")
            return redirect(url_for("main.mainpage"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html", form=form)

# Logout Route
@main.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out!", "info")
    return redirect(url_for("login"))

class RegisterForm(FlaskForm):
    user_id = StringField('User ID', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    submit = SubmitField('Register')

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user_id = form.user_id.data
        password = form.password.data
        password2 = form.password2.data

        if password != password2:
            flash("Passwords do not match!", "danger")
        else:
            flash(f"Registration feature not implemented yet. You entered: {user_id}, {password}", "info")
            return redirect(url_for('main.register'))  # Refresh the page after "registration"
        
        if user_exists(user_id):
            flash("Username already exists!", "danger")
        else:
            if add_user(user_id, password):
                flash("Registration successful! Please login.", "success")
                return redirect(url_for("main.login"))
            else:
                flash("Registration failed. Please try again.", "danger")

    return render_template('register.html', form=form)

@main.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')  # Get the search query from the URL parameters
    return f" searched for: {query}"