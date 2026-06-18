from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.controllers.customer import get_dashboard_data, update_customer_profile

customer_bp = Blueprint("customer", __name__)


def login_required(view):
    """Redirect to login if no customer is signed in."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("customer_id"):
            flash("Please log in to continue.")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


@customer_bp.route("/dashboard")
@login_required
def dashboard():
    data = get_dashboard_data(session["customer_id"])
    return render_template("dashboard.html", **data)


@customer_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    customer_id = session["customer_id"]

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        success, message = update_customer_profile(customer_id, full_name, phone, address)
        flash(message)
        return redirect(url_for("customer.profile"))

    data = get_dashboard_data(customer_id)
    return render_template("profile.html", customer=data["customer"])


@customer_bp.route("/orders")
@login_required
def orders():
    data = get_dashboard_data(session["customer_id"])
    return render_template("orders.html", recent_orders=data["recent_orders"])
