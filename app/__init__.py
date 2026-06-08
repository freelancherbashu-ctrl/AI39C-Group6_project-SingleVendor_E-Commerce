from flask import Flask
from app.extensions import mysql

def create_app():
    app = Flask(__name__)
    app.config.from_object("config")
    mysql.init_app(app)

    from app.routes.authroute import auth_bp
    app.register_blueprint(auth_bp)

    with app.app_context():
        from app.models.order import Order
        from app.models.user import User
        User.init_table(mysql)
        Order.init_table(mysql)

    return app
