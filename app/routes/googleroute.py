from flask import Blueprint, redirect, url_for, session, flash
from flask_dance.contrib.google import make_google_blueprint, google
from app.models.user import User
from app.extensions import mysql

google_callback_bp = Blueprint("google_auth", __name__)

def create_google_blueprint(app):
    bp = make_google_blueprint(
        client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
        scope=["openid",
               "https://www.googleapis.com/auth/userinfo.email",
               "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_to="google_auth.after_google_login"
    )
    return bp

@google_callback_bp.route("/login/google/done")
def after_google_login():
    if not google.authorized:
        flash("Google login failed.", "error")
        return redirect(url_for("auth.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Could not get info from Google.", "error")
        return redirect(url_for("auth.login"))

    info      = resp.json()
    google_id = info["id"]
    email     = info["email"]
    full_name = info.get("name", email.split("@")[0])

    user = User.get_or_create_google_user(mysql, google_id, email, full_name)

    # Fetch full user so profile_picture is included in session
    from app.models.user import User as UserModel
    full = UserModel.get_by_id(mysql, user["id"])
    session["user"] = {
        "id":              full["id"],
        "full_name":       full["full_name"],
        "email":           full["email"],
        "profile_picture": full["profile_picture"]
    }

    flash(f"Welcome, {full_name}!", "success")
    return redirect(url_for("auth.home"))