"""Auth hook for admin routes.

Customer/login side is built by another teammate. Until their auth module
lands, `admin_required` is a no-op pass-through so the admin panel stays
usable during development.

WHEN THE AUTH MODULE IS READY:
  - Replace the body of `admin_required` with a real check, e.g.:

      from flask import session, redirect, url_for, flash
      from functools import wraps

      def admin_required(view):
          @wraps(view)
          def wrapped(*args, **kwargs):
              if not session.get("is_admin"):
                  flash("Please log in as admin.", "warning")
                  return redirect(url_for("auth.login"))
              return view(*args, **kwargs)
          return wrapped

  - No other file needs to change; every admin route is gated via
    @admin_bp.before_request @admin_required (see admin_routes.py).
"""
from functools import wraps


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        # TODO: integrate with auth teammate's session check
        return view(*args, **kwargs)
    return wrapped
