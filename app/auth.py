from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login first.",
                "warning"
            )

            return redirect(
                url_for(
                    "authroutes.login"
                )
            )

        return f(*args, **kwargs)

    return decorated


def admin_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        # LOGIN CHECK

        if "user_id" not in session:

            flash(
                "Please login first.",
                "warning"
            )

            return redirect(
                url_for(
                    "authroutes.login"
                )
            )

        # ADMIN CHECK

        if session.get("role") != "admin":

            flash(
                "Admin only",
                "danger"
            )

            return redirect(
                url_for(
                    "authroutes.login"
                )
            )

        return f(*args, **kwargs)

    return decorated