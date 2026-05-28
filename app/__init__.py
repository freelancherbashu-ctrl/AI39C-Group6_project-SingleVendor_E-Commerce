from flask import Flask
import config

from app.models.database import Database
from app.routes.authroutes import AuthRoutes

def create_app():

    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY

    # create tables automatically
    with app.app_context():
        Database.create_tables()

    # register routes
    auth_routes = AuthRoutes()
    app.register_blueprint(auth_routes.register())

    return app