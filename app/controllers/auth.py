from flask import render_template, session, request, redirect, url_for, flash
from app.data.products import products
from app.data.categories import categories


class AuthController:

    # ---------------- AUTH PAGES ----------------

    def profile(self):
        return render_template("profile.html")

    
    def all_categories(self):

        search = request.args.get("search", "")

        filtered_categories = [

            c for c in categories

            if search.lower() in c["name"].lower()

        ]

        return render_template(
            "all_categories.html",
            categories=filtered_categories
        )
    
    def dashboard(self):

        search = request.args.get("search")

        if search:
            filtered = [
                p for p in products
                if search.lower() in p["name"].lower()
            ]
        else:
            filtered = products

        return render_template("dashboard.html", products=filtered)

    def checkout(self):
        return render_template("checkout.html")

    def single_category(self, category):

        sort = request.args.get("sort", "popular")

        filtered_products = []

        for product in products:

            if product["category"] == category:

                filtered_products.append(product)

        # SORTING

        if sort == "low":

            filtered_products.sort(
                key=lambda x: x["price"]
            )

        elif sort == "high":

            filtered_products.sort(
                key=lambda x: x["price"],
                reverse=True
            )

        return render_template(

            "single_category.html",

            products=filtered_products,

            category=category,

            sort=sort

        )

    def login(self):
        return render_template("login.html")

    def order_details(self):
        return render_template("order_details.html")

    def view_my_orders(self):
        return render_template("view_my_orders.html")

    
    def view_product(self, id):

        product = next((p for p in products if p["id"] == id), None)

        return render_template(
            "view_product.html",
            product=product
        )

    # ---------------- CART ----------------

    def cart(self):

        cart = session.get("cart", {})

        # convert product list → dictionary for fast lookup
        product_map = {str(p["id"]): p for p in products}

        return render_template(
            "cart.html",
            cart=cart,
            products=product_map
        )

    def add_to_cart(self, product_id):

        cart = session.get("cart", {})

        product_id = str(product_id)

        quantity = int(request.form.get("quantity", 1))

        if product_id in cart:

            cart[product_id] += quantity

        else:

            cart[product_id] = quantity

        session["cart"] = cart
        session.modified = True

        return redirect(url_for("auth.cart"))

    def update_cart(self, product_id):

        cart = session.get("cart", {})

        product_id = str(product_id)

        action = request.form.get("action")

        if product_id in cart:

            if action == "increase":

                cart[product_id] += 1

            elif action == "decrease":

                cart[product_id] -= 1

                if cart[product_id] <= 0:

                    cart.pop(product_id)

        session["cart"] = cart
        session.modified = True

        return redirect(url_for("auth.cart"))

    def remove_from_cart(self, product_id):

        cart = session.get("cart", {})
        product_id = str(product_id)

        if product_id in cart:
            cart.pop(product_id)

        session["cart"] = cart

        flash("Item removed from cart", "success")
        return redirect(url_for("auth.cart"))


# create ONE instance
auth_controller = AuthController()