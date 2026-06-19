from flask import Blueprint, render_template, request

from app.models.product_models import Product

product_bp = Blueprint("product", __name__)


@product_bp.route("/products")
def listing():
    search = request.args.get("search", "").strip()
    selected_category = request.args.get("category", "").strip()
    products = Product.get_all(
        category=selected_category or None,
        search=search or None,
    )
    categories = Product.get_categories()
    return render_template(
        "products.html",
        products=products,
        categories=categories,
        search=search,
        selected_category=selected_category,
    )


@product_bp.route("/products/<int:product_id>")
def detail(product_id):
    product = Product.find_by_id(product_id)
    if not product or not product["is_active"]:
        return render_template("404.html"), 404
    return render_template("product_detail.html", product=product)
