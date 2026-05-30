from flask import session, flash, redirect, url_for, request

class BaseController:
    def get_form_data(self, *fields):
        return tuple(request.form.get(field, "").strip() for field in fields)
    
    def is_logged_in(self):
        return "user_id" in session
    
    def get_current_role(self):
        return session.get("role")
    
    def check_admin(self):
        # Temporary: Allow all access (since no auth system yet)
        # TODO: Add proper authentication later
        return None