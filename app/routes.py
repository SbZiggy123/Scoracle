
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

main = Blueprint('main', __name__)

@main.route('/')
def mainpage():
    return render_template("base.html")

@main.route('/PremierLeague')
def mainpage():
    return render_template("PremierLeague.html")

@main.route('/createLeague')
def mainpage():
    return render_template("createLeague.html")

@main.route('/currentLeagues')
def mainpage():
    return render_template("currentLeagues.html")

@main.route('/fixtures')
def mainpage():
    return render_template("fixtures.html")

@main.route('/joinLeague')
def mainpage():
    return render_template("joinLeague.html")

@main.route('/results')
def mainpage():
    return render_template("results.html")


def get_user(username):
    #replace this with an actual query from the database
    fake_users = {"user1": "password123", "user2": "secret"}
    return {"username": username, "password": fake_users.get(username)} if username in fake_users else None

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

        if user and user["password"] == password:
            session["user"] = username  # Store user session
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html", form=form)

# Logout Route
@main.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out!", "info")
    return redirect(url_for("login"))

@main.route('/register')
def mainpage():
    return render_template("register.html")