from werkzeug.security import check_password_hash, generate_password_hash
from flask import session

from app.models.user_models import Customer


def register_customer(full_name, email, phone, address, password):
    """Create a new customer account. Returns (success, message)."""
    if not full_name or not email or not password:
        return False, "Full name, email and password are required."

    existing = Customer.find_by_email(email)
    if existing:
        return False, "An account with this email already exists."

    password_hash = generate_password_hash(password)
    Customer.create(full_name, email, phone, address, password_hash)
    return True, "Account created successfully. Please log in."


def login_customer(email, password):
    """Validate credentials and start a session. Returns (success, message)."""
    customer = Customer.find_by_email(email)
    if not customer:
        return False, "Invalid email or password."

    if not check_password_hash(customer["password_hash"], password):
        return False, "Invalid email or password."

    session["customer_id"] = customer["id"]
    session["customer_name"] = customer["full_name"]
    return True, "Logged in successfully."


def logout_customer():
    """Clear the current customer session."""
    session.pop("customer_id", None)
    session.pop("customer_name", None)


def get_current_customer():
    """Return the logged-in customer's full record, or None."""
    customer_id = session.get("customer_id")
    if not customer_id:
        return None
    return Customer.find_by_id(customer_id)
