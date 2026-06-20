from app.models.cart_models import CartItem
from app.models.order_models import Order, OrderItem
from app.models.product_models import Product


def place_order(customer_id):
    """Convert the customer's cart into a confirmed order.
    Returns (success, message, order_id)."""
    items = CartItem.get_cart(customer_id)
    if not items:
        return False, "Your cart is empty.", None

    # Validate stock for every item before touching anything
    for item in items:
        product = Product.find_by_id(item["product_id"])
        if not product or product["stock"] < item["quantity"]:
            return (
                False,
                f"'{item['name']}' does not have enough stock. Please update your cart.",
                None,
            )

    total = sum(item["line_total"] for item in items)
    order_id = Order.create(customer_id, total)

    for item in items:
        OrderItem.create(
            order_id,
            item["product_id"],
            item["name"],
            item["quantity"],
            item["price"],
        )
        Product.update_stock(item["product_id"], -item["quantity"])

    CartItem.clear(customer_id)
    return True, "Order placed successfully!", order_id
