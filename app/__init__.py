from flask import Flask
from app.routes.authroute import auth_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "meropasal_secret_key"
    app.register_blueprint(auth_bp)
    return app