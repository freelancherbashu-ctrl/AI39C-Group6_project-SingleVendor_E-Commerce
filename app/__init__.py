# from flask import Flask
# import config

# def create_app():
#     app = Flask(__name__)
#     app.secret_key = config.SECRET_KEY
#     app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    
#     from app.routes.category_routes import category_bp
#     app.register_blueprint(category_bp)
    
#     from app.routes.product_routes import product_bp
#     app.register_blueprint(product_bp)
    
#     return app


from flask import Flask
from app.models.database import Database
from app.routes.category_routes import category_bp
from app.routes.product_routes import product_bp
import config

def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    
    with app.app_context():
        Database.create_tables()
    
    app.register_blueprint(category_bp)
    app.register_blueprint(product_bp)
    
    return app