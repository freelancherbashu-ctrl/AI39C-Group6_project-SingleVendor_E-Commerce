from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from app.controllers.base_controller import BaseController
from app.models.user_model import User
from app.models.database import Database
import uuid


class AuthController(BaseController):

    def __init__(self):
        self.user_model = User()

    # ================= REGISTER =================
    def register(self):

        if request.method == "GET":
            return render_template("register.html")

        name, email = self.get_form_data("name", "email")
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields required", "danger")
            return redirect(url_for("authroutes.register"))

        if len(password) < 6:
            flash("Password must be 6+ characters", "danger")
            return redirect(url_for("authroutes.register"))

        if self.user_model.find_by("email", email):
            flash("Email already exists", "danger")
            return redirect(url_for("authroutes.register"))

        hashed_password = generate_password_hash(password)

        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role="user"
        )

        user.save()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("authroutes.login"))

    # ================= LOGIN =================
    def login(self):

        if request.method == "GET":
            return render_template("login.html")

        email, password = self.get_form_data("email", "password")

        user_data = self.user_model.find_by("email", email)

        if not user_data:
            flash("Invalid email or password", "danger")
            return redirect(url_for("authroutes.login"))

        user = User.from_db(user_data)

        if user_data["password"] != password:
            flash("Invalid email or password", "danger")
            return redirect(url_for("authroutes.login"))

        # SESSION SET
        session.clear()
        session.permanent = True

        session["user_id"] = user_data["id"]
        session["user_name"] = user_data["name"]
        session["role"] = user_data["role"]

        flash("Login successful!", "success")

        # ROLE BASED REDIRECT
        if user_data["role"] == "admin":
            return redirect(url_for("authroutes.admin_dashboard"))
        else:
            return redirect(url_for("authroutes.customer_dashboard"))

    # ================= LOGOUT =================
    def logout(self):
        session.clear()
        flash("Logged out successfully!", "success")
        return redirect(url_for("authroutes.login"))

    # ================= ADMIN DASHBOARD =================
    def admin_dashboard(self):

        return render_template(
            "admin_dashboard.html"
        )

    # ================= CUSTOMER DASHBOARD =================
    def customer_dashboard(self):

        return render_template(
            "customer_dashboard.html"
        )

    # ================= FORGOT PASSWORD =================
    def forgot_password(self):

        if request.method == "POST":

            email = request.form.get("email")

            user = self.user_model.find_by("email", email)

            if not user:

                flash("Email not found","danger")
                return render_template(
                    "forgot_password.html"
                )

            token = str(uuid.uuid4())

            db = Database()

            db.execute(

                "UPDATE users SET reset_token=%s WHERE email=%s",

                (token,email)

            )

            db.close()

            reset_link = url_for(
                "authroutes.reset_password",
                token=token,
                _external=True
            )

            return render_template(

                "forgot_password.html",

                reset_link=reset_link

            )

        return render_template(
            "forgot_password.html"
        )

    # ================= RESET PASSWORD =================
    def reset_password(self, token):

        db = Database()

        user = db.fetch_one(

            "SELECT * FROM users WHERE reset_token=%s",

            (token,)

        )

        if not user:

            flash("Invalid Link","danger")

            return redirect(
                url_for("authroutes.login")
            )

        if request.method=="POST":

            password=request.form.get(
                "password"
            )

            confirm=request.form.get(
                "confirm_password"
            )

            if password != confirm:

                flash(
                    "Passwords do not match",
                    "danger"
                )

                return render_template(
                    "reset_password.html"
                )

            db.execute(

            """
            UPDATE users
            SET password=%s,
            reset_token=NULL
            WHERE id=%s
            """,

            (password,user["id"])

            )

            flash(
            "Password Updated",
            "success"
            )

            return redirect(
            url_for("authroutes.login")
            )

        return render_template(
        "reset_password.html"
        )

    # ================= HOME =================
    def home(self):
        return render_template("home.html")

    # ================= CONTACT =================
    def contact(self):
        return render_template("contact.html")
