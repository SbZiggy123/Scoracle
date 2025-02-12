from flask import Flask
from flask_session import Session
from .models import init_db

def create_app():
    app = Flask(__name__)
    app.secret_key = "score_oracle"
    
    #session config
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  

    # Load configuration
    app.config.from_object('config')
    
    Session(app)

    # Register routes
    from .routes import main
    app.register_blueprint(main)

    return app