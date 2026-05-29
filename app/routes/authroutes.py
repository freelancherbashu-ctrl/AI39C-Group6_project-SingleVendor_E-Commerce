from flask import Blueprint
from app.controllers.auth import AuthController

from app.auth import login_required, admin_required

class AuthRoutes:

    def __init__(self):

        self.bp = Blueprint("authroutes", __name__)
        self.controller = AuthController()

    def register(self):

        # ---------------- AUTH ROUTES ----------------
        self.bp.route("/login", methods=["GET", "POST"])(
            self.controller.login
        )

        self.bp.route("/register", methods=["GET", "POST"])(
            self.controller.register
        )


        

        # ---------------- RESET FLOW ----------------
        self.bp.route("/forgot-password", methods=["GET", "POST"])(
            self.controller.forgot_password
        )

        self.bp.route("/reset_password/<token>", methods=["GET", "POST"])(
            self.controller.reset_password
        )

        # ---------------- OTHER PAGES ----------------
        self.bp.route("/home")(
            self.controller.home
        )

        self.bp.route("/contact")(
            self.controller.contact
        )
        self.bp.route('/logout')(self.controller.logout)
        self.bp.route('/customer_dashboard')(login_required(self.controller.customer_dashboard))
        self.bp.route('/admin_dashboard')(admin_required(self.controller.admin_dashboard))
        return self.bp