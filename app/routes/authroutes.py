from flask import Blueprint
from app.controllers.auth import AuthController

class AuthRoutes:
    def __init__(self):
        self.bp = Blueprint('authroutes', __name__)
        self.controller = AuthController()

    def get_routes(self):
        self.bp.route('/register', methods=['GET', 'POST'])(self.controller.register)
        self.bp.route('/login', methods=['GET', 'POST'])(self.controller.login)
        self.bp.route('/logout')(self.controller.logout)
        self.bp.route('/forgot-password', methods=['GET', 'POST'])(self.controller.forgot_password)
        self.bp.route('/reset-password/<token>', methods=['GET', 'POST'])(self.controller.reset_password)
        self.bp.route('/customer-dashboard')(self.controller.customer_dashboard)
        self.bp.route('/admin-dashboard')(self.controller.admin_dashboard)
        return self.bp