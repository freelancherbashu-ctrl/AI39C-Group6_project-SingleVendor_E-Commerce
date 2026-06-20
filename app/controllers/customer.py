from app.models.user_models import Customer
from app.models.order_models import Order


def get_dashboard_data(customer_id):
    """Gather the profile info and recent orders shown on the
    customer dashboard."""
    customer = Customer.find_by_id(customer_id)
    recent_orders = Order.find_recent_by_customer(customer_id, limit=5)
    order_count = Order.count_by_customer(customer_id)

    return {
        "customer": customer,
        "recent_orders": recent_orders,
        "order_count": order_count,
    }


def update_customer_profile(customer_id, full_name, phone, address):
    """Update editable profile fields for a customer. Returns (success, message)."""
    if not full_name:
        return False, "Full name cannot be empty."

    Customer.update_profile(customer_id, full_name, phone, address)
    return True, "Profile updated successfully."
