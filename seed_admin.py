"""Insert sample data so the admin dashboard isn't empty.
Run once:  python seed_admin.py
"""
from app import create_app
from app.models.database import db
from app.models.product_models import Category, Product, Order, OrderItem

app = create_app()

with app.app_context():
    if Category.query.count() == 0:
        electronics = Category(name="Electronics", description="Phones, laptops, accessories")
        clothing    = Category(name="Clothing",    description="Men & women apparel")
        grocery     = Category(name="Grocery",     description="Daily essentials")
        db.session.add_all([electronics, clothing, grocery])
        db.session.commit()

        db.session.add_all([
            Product(name="Samsung Galaxy A15", description='6.5" display, 128GB',
                    price=24999, stock=10, category_id=electronics.id),
            Product(name="Wireless Earbuds", description="Bluetooth 5.3",
                    price=2499, stock=25, category_id=electronics.id),
            Product(name="Men's T-shirt", description="Cotton, all sizes",
                    price=799, stock=3, category_id=clothing.id),
            Product(name="Basmati Rice 5kg", description="Premium quality",
                    price=1100, stock=40, category_id=grocery.id),
        ])
        db.session.commit()

        o1 = Order(customer_name="Ram Bahadur", customer_email="ram@example.com",
                   customer_phone="9800000001", address="Kathmandu",
                   total_amount=24999, status="pending")
        o2 = Order(customer_name="Sita Sharma", customer_email="sita@example.com",
                   customer_phone="9800000002", address="Lalitpur",
                   total_amount=3298, status="completed")
        db.session.add_all([o1, o2])
        db.session.commit()

        db.session.add_all([
            OrderItem(order_id=o1.id, product_name="Samsung Galaxy A15", quantity=1, price=24999),
            OrderItem(order_id=o2.id, product_name="Wireless Earbuds",   quantity=1, price=2499),
            OrderItem(order_id=o2.id, product_name="Men's T-shirt",      quantity=1, price=799),
        ])
        db.session.commit()
        print("✓ Sample data inserted.")
    else:
        print("Data already exists — skipping.")
