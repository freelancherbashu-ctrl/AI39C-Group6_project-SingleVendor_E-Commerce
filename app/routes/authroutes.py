from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.controllers.auth import login_customer, logout_customer, register_customer

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")

        success, message = register_customer(full_name, email, phone, address, password)
        flash(message)
        if success:
            return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        success, message = login_customer(email, password)
        flash(message)
        if success:
            return redirect(url_for("customer.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_customer()
    return redirect(url_for("auth.login"))
