from flask import Flask
import config
from app.models.database import Database
from app.routes.authroutes import AuthRoutes

def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY

    with app.app_context():
        Database.create_tables()

    auth_routes = AuthRoutes()
    app.register_blueprint(auth_routes.register())

    return app