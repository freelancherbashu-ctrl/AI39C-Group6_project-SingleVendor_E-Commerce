from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from app.controllers.base_controller import BaseController
from app.models.user_model import User
from app.models.database import Database
import uuid
import os
import random
from functools import wraps
from flask import render_template, session, request, redirect, url_for, flash, jsonify
import config as _cfg
from werkzeug.utils import secure_filename
from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.user import User
from app.models.wishlist import Wishlist
from app.models.flash_sale import FlashSale
from app.models.review import Review
from app.extensions import mysql, mail

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'profile_pics')
ALLOWED_EXT   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class AuthController(BaseController):

    def __init__(self):
        self.user_model = User()

    # ================= PROFILE =================
    def profile(self):
        if 'user_id' not in session:
            return redirect(url_for('authroutes.login'))
        db = Database()
        user = db.fetch_one("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        db.close()
        return render_template('profile.html', user=user)

    # ================= EDIT PROFILE =================
    def edit_profile(self):
        if 'user_id' not in session:
            return redirect(url_for('authroutes.login'))
        db = Database()
        user = db.fetch_one("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            existing = db.fetch_one("SELECT * FROM users WHERE email = %s AND id != %s", (email, session['user_id']))
            if existing:
                flash('Email already exists!', 'danger')
                return redirect(url_for('authroutes.edit_profile'))
            db.execute("UPDATE users SET name = %s, email = %s WHERE id = %s", (name, email, session['user_id']))
            db.close()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('authroutes.profile'))
        db.close()
        return render_template('edit_profile.html', user=user)

    # ================= CHANGE PASSWORD =================
    def change_password(self):
        if 'user_id' not in session:
            return redirect(url_for('authroutes.login'))
        db = Database()
        user = db.fetch_one("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        if request.method == 'POST':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            if not check_password_hash(user['password'], old_password):
                flash('Old password is incorrect!', 'danger')
                return redirect(url_for('authroutes.change_password'))
            if new_password != confirm_password:
                flash('New passwords do not match!', 'danger')
                return redirect(url_for('authroutes.change_password'))
            if len(new_password) < 6:
                flash('Password must be at least 6 characters!', 'danger')
                return redirect(url_for('authroutes.change_password'))
            hashed = generate_password_hash(new_password)
            db.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, session['user_id']))
            db.close()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('authroutes.profile'))
        db.close()
        return render_template('change_password.html', user=user)

    # ================= UPLOAD PHOTO =================
    def upload_photo(self):
        if 'user_id' not in session:
            return redirect(url_for('authroutes.login'))
        ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
        if 'photo' not in request.files:
            flash('No file selected!', 'danger')
            return redirect(url_for('authroutes.profile'))
        file = request.files['photo']
        if file.filename == '':
            flash('No file selected!', 'danger')
            return redirect(url_for('authroutes.profile'))
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            flash('Only JPG, PNG and GIF files allowed!', 'danger')
            return redirect(url_for('authroutes.profile'))
        filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
        upload_folder = os.path.join(current_app.static_folder, 'images', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        db = Database()
        db.execute("UPDATE users SET profile_picture = %s WHERE id = %s", (filename, session['user_id']))
        db.close()
        flash('Profile picture updated!', 'success')
        return redirect(url_for('authroutes.profile'))

    # ================= REGISTER =================
    def register(self):
        if request.method == "GET":
           return render_template("register.html")

        name, email = self.get_form_data("name", "email")
        password = request.form.get("password", "")

        if not name or not email or not password:
           flash("All fields required", "danger")
           return redirect(url_for("authroutes.register"))

        if len(password) < 6:
           flash("Password must be 6+ characters", "danger")
           return redirect(url_for("authroutes.register"))

        if self.user_model.find_by("email", email):
           flash("Email already exists", "danger")
           return redirect(url_for("authroutes.register"))

        hashed_password = generate_password_hash(password)

        user = User(
           name=name,
           email=email,
           password=hashed_password,
           role="user"
        )

        user.save()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("authroutes.login"))
    # ================= LOGIN =================
    def login(self):
        if request.method == "GET":
            return render_template("login.html")

        email, password = self.get_form_data("email", "password")

        user_data = self.user_model.find_by("email", email)
    
        if not user_data:
           flash("Invalid email or password", "danger")
           return redirect(url_for("authroutes.login"))

        if not check_password_hash(user_data["password"], password):
           flash("Invalid email or password", "danger")
           return redirect(url_for("authroutes.login"))

        session.clear()
        session.permanent = True
        session["user_id"] = user_data["id"]
        session["user_name"] = user_data["name"]
        session["role"] = user_data["role"]
 
        flash("Login successful!", "success")

        if user_data["role"] == "admin":
           return redirect(url_for("authroutes.admin_dashboard"))
        else:
           return redirect(url_for("authroutes.customer_dashboard"))
    # ================= LOGOUT =================
    def logout(self):
        session.clear()
        flash("Logged out successfully!", "success")
        return redirect(url_for("authroutes.login"))

    # ================= ADMIN DASHBOARD =================
    def admin_dashboard(self):

        return render_template(
            "admin_dashboard.html"
        )

    # ================= CUSTOMER DASHBOARD =================
    def customer_dashboard(self):

        return render_template(
            "customer_dashboard.html"
        )

    # ================= FORGOT PASSWORD =================
    def forgot_password(self):
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            result = User.create_otp(mysql, email)
            if result == "google_account":
                flash("This account uses Google login. Please sign in with Google instead.", "error")
                return redirect(url_for("auth.forgot_password"))
            if result:
                otp = result
                from flask_mail import Message
                msg = Message(subject="MeroPasal — Password Reset OTP", recipients=[email])
                msg.body = f"Hi,\n\nYour MeroPasal password reset OTP is: {otp}\n\nThis code is valid for 15 minutes. Do not share it with anyone.\n\n— MeroPasal Team"
                msg.html = f"""<p>Hi,</p><p>Your <strong>MeroPasal</strong> password reset OTP is:</p>
<h2 style="letter-spacing:8px;font-size:32px;color:#4f46e5;">{otp}</h2>
<p>This code is valid for <strong>15 minutes</strong>. Do not share it with anyone.</p><p>— MeroPasal Team</p>"""
                try:
                    mail.send(msg)
                    session["otp_email"] = email
                    session.modified = True
                    flash("A 6-digit OTP has been sent to your email.", "success")
                    return redirect(url_for("auth.verify_otp"))
                except Exception:
                    flash("Could not send email. Please try again later.", "error")
            else:
                flash("If that email exists, an OTP has been sent.", "success")
            return redirect(url_for("auth.forgot_password"))
        return render_template("forgot_password.html", cart_count=_cart_count())

    def verify_otp(self):
        email = session.get("otp_email")
        if not email:
            flash("Session expired. Please request a new OTP.", "error")
            return redirect(url_for("auth.forgot_password"))
        if request.method == "POST":
            entered = request.form.get("otp", "").strip()
            token = User.verify_otp(mysql, email, entered)
            if token:
                session.pop("otp_email", None)
                session.modified = True
                flash("OTP verified! Please set your new password.", "success")
                return redirect(url_for("auth.reset_password", token=token))
            else:
                flash("Invalid or expired OTP. Please try again.", "error")
        return render_template("verify_otp.html", email=email, cart_count=_cart_count())

    def reset_password(self, token):
        db = Database()
        user = db.fetch_one("SELECT * FROM users WHERE reset_token=%s", (token,))
        if not user:
            flash("Invalid Link", "danger")
            return redirect(url_for("authroutes.login"))
        if request.method == "POST":
            password = request.form.get("password")
            confirm = request.form.get("confirm_password")
            if password != confirm:
                flash("Passwords do not match", "danger")
                return render_template("reset_password.html")
            db.execute("UPDATE users SET password=%s, reset_token=NULL WHERE id=%s", (password, user["id"]))
            flash("Password Updated", "success")
            return redirect(url_for("authroutes.login"))
        return render_template("reset_password.html")

    # ================= HOME =================
    def home(self):
        search = request.args.get("search", "").strip()
        sort   = request.args.get("sort", "popular")
        if not search:
            filtered_products   = Product.get_all(mysql)
            matching_categories = []
        else:
            filtered_products   = Product.search(mysql, search)
            all_cats = Category.get_all(mysql)
            matching_categories = [c for c in all_cats if search.lower() in c["name"].lower()]
        if search:
            if sort == "low":
                filtered_products = sorted(filtered_products, key=lambda x: x["price"])
            elif sort == "high":
                filtered_products = sorted(filtered_products, key=lambda x: x["price"], reverse=True)
        sales    = FlashSale.get_active(mysql)
        sale_map = {s["product_id"]: s for s in sales}
        pids = [p["id"] for p in filtered_products]
        rating_map = Review.get_avg_ratings_bulk(mysql, pids)
        return render_template("home_page.html", products=filtered_products,
                               matching_categories=matching_categories, sort=sort,
                               flash_sales=sales, sale_map=sale_map,
                               rating_map=rating_map,
                               cart_count=_cart_count(), user=_current_user())

    def all_categories(self):
        return render_template("all_categories.html", categories=Category.get_all(mysql),
                               cart_count=_cart_count(), user=_current_user())

    def single_category(self, category):
        sort     = request.args.get("sort", "popular")
        filtered = Product.get_by_category(mysql, category)
        if sort == "low":
            filtered.sort(key=lambda x: x["price"])
        elif sort == "high":
            filtered.sort(key=lambda x: x["price"], reverse=True)
        sale_map = _get_sale_map()
        pids_cat = [p["id"] for p in filtered]
        rating_map_cat = Review.get_avg_ratings_bulk(mysql, pids_cat)
        return render_template("single_category.html", products=filtered,
                               category=category, sort=sort,
                               sale_map=sale_map, rating_map=rating_map_cat,
                               cart_count=_cart_count(), user=_current_user())

    def view_product(self, id):
        product  = Product.get_by_id(mysql, id)
        sale_map = _get_sale_map()
        sale     = sale_map.get(product["id"]) if product else None
        reviews  = Review.get_for_product(mysql, id)
        avg_rating, review_count = Review.get_avg_rating(mysql, id)
        user = _current_user()
        reviewable_order_id = None
        if user and product:
            reviewable_order_id = Review.get_reviewable_orders(mysql, user["id"], id)
        return render_template("view_product.html", product=product, sale=sale,
                               reviews=reviews, avg_rating=avg_rating,
                               review_count=review_count,
                               reviewable_order_id=reviewable_order_id,
                               cart_count=_cart_count(), user=user)

    def view_product_json(self, id):
        from flask import jsonify
        product  = Product.get_by_id(mysql, id)
        if not product:
            return jsonify({"error": "Not found"}), 404
        sale_map = _get_sale_map()
        sale     = sale_map.get(product["id"])
        data = {
            "id":          product["id"],
            "name":        product["name"],
            "price":       float(product["price"]),
            "image":       product["image"],
            "description": product.get("description", ""),
            "category":    product.get("category", ""),
            "sale_price":  float(sale["sale_price"]) if sale else None,
            "discount":    int(sale["discount"])     if sale else None,
        }
        return jsonify(data)

    def categories_json(self):
        from flask import jsonify
        cats = Category.get_all(mysql)
        result = []
        for c in cats:
            result.append({
                "id":    c["id"],
                "name":  c["name"],
                "image": ("/static/" + c["image"]) if c.get("image") else "",
            })
        return jsonify(result)

    def order_details(self, order_id):
        user = _current_user()
        if not user:
            flash("Please log in to view order details.", "warning")
            return redirect(url_for("auth.login"))
        order = Order.get_by_id(mysql, order_id)
        if not order or order["user_id"] != user["id"]:
            flash("Order not found.", "danger")
            return redirect(url_for("auth.view_my_orders"))
        return render_template("order_details.html", order=order, cart_count=_cart_count())

    def order_details_json(self, order_id):
        """JSON endpoint for the order detail drawer on My Orders page."""
        from flask import jsonify
        user = _current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        order = Order.get_by_id(mysql, order_id)
        if not order or order["user_id"] != user["id"]:
            return jsonify({"error": "Not found"}), 404
        items = []
        for it in (order.get("order_items") or []):
            items.append({
                "name":     it.get("name", ""),
                "image":    it.get("image", ""),
                "qty":      it.get("qty", 1),
                "subtotal": float(it.get("subtotal", 0)),
                "on_sale":  it.get("on_sale", False),
            })
        return jsonify({
            "id":             order["id"],
            "customer_name":  order["customer_name"],
            "phone":          order["phone"],
            "area":           order.get("area", ""),
            "city":           order.get("city", ""),
            "district":       order.get("district", ""),
            "province":       order.get("province", ""),
            "landmark":       order.get("landmark", ""),
            "payment_method": order.get("payment_method", ""),
            "payment_status": order.get("payment_status", "Pending"),
            "order_status":   order["order_status"],
            "total_price":    float(order["total_price"]),
            "created_at":     order["created_at"].strftime("%d %b %Y, %I:%M %p") if order.get("created_at") else "",
            "items":          items,
        })

    # __ CART ──────────────────────────────────────────────────────────────────

    def cart(self):
        session.pop("buy_now", None)
        session.modified = True
        cart     = session.get("cart", {})
        sale_map = _get_sale_map()
        product_map = {}
        stale_pids  = []
        for pid in cart:
            p = Product.get_by_id(mysql, int(pid))
            if p:
                sale = sale_map.get(p["id"])
                if sale:
                    p["sale_price"]     = sale["sale_price"]
                    p["discount"]       = sale["discount"]
                    p["original_price"] = p["price"]
                    p["on_sale"]        = True
                else:
                    p["on_sale"] = False
                product_map[pid] = p
            else:
                stale_pids.append(pid)
        if stale_pids:
            for pid in stale_pids:
                cart.pop(pid, None)
            session["cart"] = cart
            session.modified = True
            flash(f"{len(stale_pids)} item(s) were removed from your cart because they are no longer available.", "error")
        return render_template("cart.html", cart=cart, products=product_map,
                               cart_count=_cart_count(), user=_current_user())

    def add_to_cart(self, product_id):
        if not session.get("user"):
            flash("Please log in to add items to your cart.", "error")
            return redirect(url_for("auth.login"))
        product = Product.get_by_id(mysql, product_id)
        if not product:
            flash("Product not found.", "error")
            return redirect(url_for("auth.home"))
        if product["available"] == 0:
            flash(f"Sorry, {product['name']} is out of stock.", "error")
            return redirect(url_for("auth.view_product", id=product_id))
        cart    = session.get("cart", {})
        pid     = str(product_id)
        qty     = int(request.form.get("quantity", 1))
        new_qty = cart.get(pid, 0) + qty
        if new_qty > product["available"]:
            flash(f"Only {product['available']} unit(s) available.", "error")
            new_qty = product["available"]
        cart[pid] = new_qty
        session["cart"] = cart
        session.modified = True
        # Remove from wishlist if present
        if session.get("user"):
            Wishlist.remove(mysql, session["user"]["id"], product_id)
        flash("Added to cart!", "success")
        return redirect(url_for("auth.view_product", id=product_id))

    def update_cart(self, product_id):
        cart   = session.get("cart", {})
        pid    = str(product_id)
        action = request.form.get("action")
        if pid in cart:
            if action == "increase":
                cart[pid] += 1
            elif action == "decrease":
                cart[pid] -= 1
                if cart[pid] <= 0:
                    cart.pop(pid)
        session["cart"] = cart
        session.modified = True
        return redirect(url_for("auth.cart"))

    def remove_from_cart(self, product_id):
        cart = session.get("cart", {})
        cart.pop(str(product_id), None)
        session["cart"] = cart
        session.modified = True
        flash("Item removed from cart.", "success")
        return redirect(url_for("auth.cart"))

    # ── BUY NOW ───────────────────────────────────────────────────────────────

    def buy_now(self, product_id):
        if not session.get("user"):
            flash("Please log in to purchase.", "error")
            return redirect(url_for("auth.login"))
        p = Product.get_by_id(mysql, product_id)
        if not p:
            flash("Product not found.", "error")
            return redirect(url_for("auth.home"))
        sale_map = _get_sale_map()
        sale = sale_map.get(p["id"])
        price = sale["sale_price"] if sale else p["price"]
        qty = int(request.form.get("quantity", 1))
        session["buy_now"] = {
            "id": p["id"], "name": p["name"], "price": price,
            "original_price": p["price"], "on_sale": bool(sale),
            "image": p["image"], "qty": qty, "subtotal": price * qty
        }
        session.modified = True
        return redirect(url_for("auth.checkout"))

    # ── CHECKOUT ──────────────────────────────────────────────────────────────

    def checkout(self):
        if not session.get("user"):
            flash("Please log in to checkout.", "error")
            return redirect(url_for("auth.login"))
        buy_now = session.get("buy_now")
        cart    = session.get("cart", {})
        if buy_now:
            items = [buy_now]
            total = buy_now["subtotal"]
        elif cart:
            session.pop("buy_now", None)
            session.modified = True
            items = _build_items_snapshot(cart)
            total = _calc_total(items)
        else:
            flash("Nothing to checkout.", "error")
            return redirect(url_for("auth.home"))
        delivery_fee = 0 if total >= _cfg.FREE_DELIVERY_THRESHOLD else _cfg.DELIVERY_FEE
        grand_total  = total + delivery_fee
        return render_template("checkout.html", items=items, total=total,
                               delivery_fee=delivery_fee, grand_total=grand_total,
                               free_threshold=_cfg.FREE_DELIVERY_THRESHOLD,
                               cart_count=_cart_count(), user=_current_user())

    def place_order(self):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        buy_now = session.get("buy_now")
        cart    = session.get("cart", {})
        if buy_now:
            items = [buy_now]
        elif cart:
            items = _build_items_snapshot(cart)
        else:
            return redirect(url_for("auth.home"))
        total          = _calc_total(items)
        delivery_fee   = 0 if total >= _cfg.FREE_DELIVERY_THRESHOLD else _cfg.DELIVERY_FEE
        # Coupon discount
        coupon_id      = request.form.get("coupon_id", type=int)
        discount_amount = request.form.get("discount_amount", 0, type=float)
        if coupon_id and discount_amount > 0:
            from app.models.coupon import Coupon
            user = _current_user()
            coupon_check, _ = Coupon.validate(mysql, 
                request.form.get("coupon_code",""), user["id"] if user else 0, total)
            if not coupon_check:
                discount_amount = 0
                coupon_id = None
        grand_total    = max(0, total + delivery_fee - discount_amount)
        payment_method = request.form.get("payment")
        order_data = {
            "user_id":  session["user"]["id"],
            "name":     request.form.get("name"),
            "phone":    request.form.get("phone"),
            "province": request.form.get("province"),
            "district": request.form.get("district"),
            "city":     request.form.get("city"),
            "area":     request.form.get("area"),
            "address":  request.form.get("address"),
            "landmark": request.form.get("landmark", ""),
            "payment":  payment_method,
            "total":    grand_total,
            "items":    items,
        }

        if payment_method in ("esewa", "khalti"):
            # Store only lightweight data in session to avoid 4KB cookie limit
            session["pending_order_data"] = {
                "user_id":  order_data["user_id"],
                "name":     order_data["name"],
                "phone":    order_data["phone"],
                "province": order_data["province"],
                "district": order_data["district"],
                "city":     order_data["city"],
                "area":     order_data["area"],
                "address":  order_data["address"],
                "landmark": order_data["landmark"],
                "payment":  order_data["payment"],
                "total":    order_data["total"],
                "items":    [{"id": i["id"], "qty": i["qty"]} for i in items],
            }
            session["last_order_total"] = grand_total
            session.modified = True
            return redirect(url_for("auth.payment", method=payment_method))

        # COD — create order immediately
        order_id, failed = Order.create(mysql, order_data)
        if failed:
            flash(f"Sorry, the following item(s) are out of stock: {', '.join(failed)}. Please update your cart.", "error")
            return redirect(url_for("auth.cart"))

        # Apply coupon usage if present
        if coupon_id and discount_amount > 0 and order_id:
            from app.models.coupon import Coupon
            user2 = _current_user()
            if user2:
                Coupon.apply(mysql, coupon_id, user2["id"], order_id)

        session.pop("buy_now", None)
        session["cart"] = {}
        session.modified = True
        return redirect(url_for("auth.order_confirmed", order_id=order_id))

    # ── PAYMENT ───────────────────────────────────────────────────────────────

    def payment(self, method):
        qr_codes = {"esewa": "images/esewa_qr.png", "khalti": "images/khalti_qr.png"}
        total    = session.get("last_order_total", None)
        order_id = session.get("last_order_id", None)
        return render_template("payment.html", method=method,
                               qr=qr_codes.get(method), total=total,
                               order_id=order_id,
                               cart_count=_cart_count(), user=_current_user())

    def submit_payment(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        transaction_code = request.form.get("transaction_code", "").strip()
        if not transaction_code:
            flash("Please enter your transaction code.", "error")
            return redirect(url_for("auth.view_my_orders"))

        order_data = session.get("pending_order_data")
        if not order_data:
            flash("Session expired. Please place your order again.", "error")
            return redirect(url_for("auth.cart"))

        # Rebuild full items snapshot from slim {id, qty} pairs stored in session
        slim_items = order_data.get("items", [])
        sale_map   = _get_sale_map()
        full_items = []
        for entry in slim_items:
            p = Product.get_by_id(mysql, int(entry["id"]))
            if p:
                sale  = sale_map.get(p["id"])
                price = sale["sale_price"] if sale else p["price"]
                full_items.append({
                    "id": p["id"], "name": p["name"], "price": price,
                    "original_price": p["price"], "on_sale": bool(sale),
                    "image": p["image"], "qty": entry["qty"],
                    "subtotal": price * entry["qty"],
                })
        order_data["items"] = full_items

        # Now create the order in DB
        order_id, failed = Order.create(mysql, order_data)
        if failed:
            flash(f"Sorry, the following item(s) are out of stock: {', '.join(failed)}. Please update your cart.", "error")
            session.pop("pending_order_data", None)
            session.modified = True
            return redirect(url_for("auth.cart"))

        # Save transaction code
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE orders SET transaction_code=%s WHERE id=%s",
            (transaction_code, order_id)
        )
        mysql.connection.commit()

        # Clear session
        session.pop("pending_order_data", None)
        session.pop("buy_now", None)
        session["cart"] = {}
        session.modified = True

        flash("Payment submitted! We'll verify your transaction code and confirm your order.", "success")
        return redirect(url_for("auth.order_confirmed", order_id=order_id))

    # ── ORDERS ────────────────────────────────────────────────────────────────

    def order_confirmed(self, order_id):
        user  = _current_user()
        order = Order.get_by_id(mysql, order_id)
        if not order or (user and order["user_id"] != user["id"]):
            flash("Order not found.", "error")
            return redirect(url_for("auth.home"))
        return render_template("order_confirmed.html", order=order,
                               cart_count=_cart_count(), user=user)

    def view_my_orders(self):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        orders = Order.get_all_by_user(mysql, session["user"]["id"])
        return render_template("view_my_orders.html", orders=orders,
                               cart_count=_cart_count(), user=_current_user())

    def cancel_order(self, order_id):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        result = Order.cancel(mysql, order_id, user["id"])
        flash("Order cancelled successfully." if result else "This order cannot be cancelled.",
              "success" if result else "error")
        return redirect(url_for("auth.view_my_orders"))

    # ── SEARCH ────────────────────────────────────────────────────────────────

    def search_suggest(self):
        q = request.args.get("q", "").strip().lower()
        if len(q) < 1:
            return jsonify([])
        suggestions = []
        for p in Product.search(mysql, q):
            suggestions.append({"label": p["name"], "type": "product",
                                "url": url_for("auth.view_product", id=p["id"])})
        for c in Category.get_all(mysql):
            if q in c["name"].lower():
                suggestions.append({"label": c["name"].title(), "type": "category",
                                    "url": url_for("auth.single_category", category=c["name"])})
        return jsonify(suggestions[:10])

    # ── WISHLIST ──────────────────────────────────────────────────────────────

    def view_wishlist(self):
        user = _current_user()
        if not user:
            flash("Please log in to view your wishlist.", "error")
            return redirect(url_for("auth.login"))
        product_ids       = Wishlist.get_product_ids(mysql, user["id"])
        wishlist_products = [p for pid in product_ids
                             for p in [Product.get_by_id(mysql, pid)] if p]
        return render_template("wishlist.html",
                               wishlist_products=wishlist_products,
                               wishlist_count=len(wishlist_products),
                               sale_map=_get_sale_map(),
                               cart_count=_cart_count(),
                               user=user)

    def toggle_wishlist(self, product_id):
        user = _current_user()
        if not user:
            return jsonify({"success": False, "error": "login_required"}), 401
        if not Product.get_by_id(mysql, product_id):
            return jsonify({"success": False, "error": "Product not found"}), 404
        already = Wishlist.is_wishlisted(mysql, user["id"], product_id)
        if already:
            Wishlist.remove(mysql, user["id"], product_id)
            wishlisted = False
            message    = "Removed from wishlist"
        else:
            Wishlist.add(mysql, user["id"], product_id)
            wishlisted = True
            message    = "Added to wishlist"
        count = Wishlist.get_count(mysql, user["id"])
        return jsonify({"success": True, "wishlisted": wishlisted,
                        "message": message, "wishlist_count": count})

    def wishlist_status(self, product_id):
        user = _current_user()
        if not user:
            return jsonify({"wishlisted": False, "wishlist_count": 0})
        count = Wishlist.get_count(mysql, user["id"])
        if product_id == 0:
            return jsonify({"wishlisted": False, "wishlist_count": count})
        wishlisted = Wishlist.is_wishlisted(mysql, user["id"], product_id)
        return jsonify({"wishlisted": wishlisted, "wishlist_count": count})
    # ── REVIEWS ───────────────────────────────────────────────────────────────

    def submit_review(self, product_id):
        from app.models.review import Review
        user = _current_user()
        if not user:
            flash("Please log in to leave a review.", "error")
            return redirect(url_for("auth.login"))
        order_id = request.form.get("order_id", type=int)
        rating   = request.form.get("rating", type=int)
        comment  = request.form.get("comment", "").strip()
        if not order_id or not rating or rating not in range(1, 6):
            flash("Invalid review submission.", "error")
            return redirect(url_for("auth.view_product", id=product_id))
        ok, err = Review.create(mysql, user["id"], product_id, order_id, rating, comment)
        if ok:
            flash("Thank you for your review!", "success")
        else:
            flash(f"Could not submit review: {err}", "error")
        return redirect(url_for("auth.view_product", id=product_id))

    # ── REFUNDS ───────────────────────────────────────────────────────────────

    def request_refund(self, order_id):
        from app.models.refund import Refund
        user = _current_user()
        if not user:
            flash("Please log in.", "error")
            return redirect(url_for("auth.login"))
        reason = request.form.get("reason", "").strip()
        if not reason:
            flash("Please provide a reason for the refund.", "error")
            return redirect(url_for("auth.view_my_orders"))
        ok, err = Refund.request(mysql, order_id, user["id"], reason)
        if ok:
            flash("Refund request submitted. We'll review it shortly.", "success")
        else:
            flash(f"Could not submit refund: {err}", "error")
        return redirect(url_for("auth.view_my_orders"))

    def my_refunds(self):
        from app.models.refund import Refund
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        refunds = Refund.get_by_user(mysql, user["id"])
        return render_template("my_refunds.html", refunds=refunds,
                               cart_count=_cart_count(), user=user)

    # ── COUPONS ───────────────────────────────────────────────────────────────

    def validate_coupon(self):
        from app.models.coupon import Coupon
        user = _current_user()
        if not user:
            return jsonify({"success": False, "message": "Please log in."}), 401
        code       = request.form.get("code", "").strip().upper()
        cart_total = request.form.get("cart_total", 0, type=float)
        coupon, err = Coupon.validate(mysql, code, user["id"], cart_total)
        if err:
            return jsonify({"success": False, "message": err})
        return jsonify({
            "success":        True,
            "coupon_id":      coupon["id"],
            "code":           coupon["code"],
            "discount_type":  coupon["discount_type"],
            "discount_value": coupon["discount_value"],
            "discount_amount": coupon["discount_amount"],
            "message":        f"Coupon applied! You save Rs. {coupon['discount_amount']:,.0f}",
        })
