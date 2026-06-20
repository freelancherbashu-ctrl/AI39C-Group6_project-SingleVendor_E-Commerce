from flask import Flask, redirect, url_for
import config

def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    
    # Register blueprint
    from app.routes.category_routes import category_bp
    app.register_blueprint(category_bp)
    
    # Homepage route
    @app.route('/')
    def home():
        return redirect(url_for('category.categories_list'))
    
    return app