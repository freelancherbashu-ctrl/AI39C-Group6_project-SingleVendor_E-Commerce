
from flask import session, flash, redirect, url_for, request


class BaseController:

    # ---------------- GET FORM DATA ----------------
    def get_form_data(self, *fields):

        return tuple(
            request.form.get(field, "").strip()
            for field in fields
        )

    # ---------------- CHECK LOGIN ----------------
    def is_logged_in(self):

        return "user_id" in session

    # ---------------- GET USER ID ----------------
    def get_current_user_id(self):

        return session.get("user_id")

    # ---------------- GET ROLE ----------------
    def get_current_role(self):

        return session.get("role")

    # ---------------- FLASH + REDIRECT ----------------
    def flash_and_redirect(self, message, category, endpoint):

        flash(message, category)

        return redirect(url_for(endpoint))
