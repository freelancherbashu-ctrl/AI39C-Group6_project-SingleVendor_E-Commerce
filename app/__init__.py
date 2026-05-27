from flask import Flask
from config import Config
from app.routes.authroutes import AuthRoutes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    auth_routes = AuthRoutes()
    app.register_blueprint(auth_routes.get_routes())

    return app