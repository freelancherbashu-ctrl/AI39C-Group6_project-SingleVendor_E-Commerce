class Product:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            price INT NOT NULL,
            category VARCHAR(80) NOT NULL,
            image VARCHAR(255) NOT NULL DEFAULT '/static/images/placeholder.png',
            description TEXT,
            stock INT NOT NULL DEFAULT 0,
            reserved INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        mysql.connection.commit()
        # Safe upgrades for existing tables
        for sql in [
            "ALTER TABLE products ADD COLUMN stock INT NOT NULL DEFAULT 0",
            "ALTER TABLE products ADD COLUMN reserved INT NOT NULL DEFAULT 0",
        ]:
            try:
                cursor.execute(sql)
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()

    @staticmethod
    def seed(mysql):
        """Insert default products only when the table is empty."""
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] > 0:
            return
        defaults = [
            ("Laptop",      200000, "electronics", "/static/images/laptop.png",
             "A powerful laptop perfect for work, study, and gaming.", 10),
            ("i-Phone",     100000, "electronics", "/static/images/iphone.png",
             "The latest iPhone with a stunning camera system.", 8),
            ("Headphones",   3000,  "electronics", "/static/images/headphones.png",
             "Premium over-ear headphones with deep bass.", 25),
            ("Hoodie",       2500,  "clothes",     "/static/images/hoodie.png",
             "A cozy and stylish hoodie made from soft fleece.", 15),
            ("Jacket",       5000,  "clothes",     "/static/images/jacket.png",
             "A durable and trendy jacket for Nepal's changing weather.", 12),
            ("Pizza",         900,  "food",        "/static/images/pizza.png",
             "Freshly baked pizza with crispy crust.", 50),
        ]
        cursor.executemany(
            "INSERT INTO products (name, price, category, image, description, stock) VALUES (%s,%s,%s,%s,%s,%s)",
            defaults
        )
        mysql.connection.commit()

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_all(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, price, category, image, description, stock, reserved
            FROM products ORDER BY id
        """)
        return [Product._row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_by_id(mysql, product_id):
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, name, price, category, image, description, stock, reserved FROM products WHERE id=%s",
            (product_id,)
        )
        row = cursor.fetchone()
        return Product._row(row) if row else None

    @staticmethod
    def get_by_category(mysql, category):
        cursor = mysql.connection.cursor()
        cursor.execute(
            """SELECT id, name, price, category, image, description, stock, reserved
               FROM products WHERE category=%s ORDER BY id""",
            (category,)
        )
        return [Product._row(r) for r in cursor.fetchall()]

    @staticmethod
    def search(mysql, query):
        cursor = mysql.connection.cursor()
        cursor.execute(
            """SELECT id, name, price, category, image, description, stock, reserved
               FROM products WHERE name LIKE %s ORDER BY id""",
            (f"%{query}%",)
        )
        return [Product._row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_low_stock(mysql, threshold=5):
        """Return products where available stock (stock - reserved) <= threshold."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, price, category, image, description, stock, reserved
            FROM products
            WHERE (stock - reserved) <= %s
            ORDER BY (stock - reserved) ASC
        """, (threshold,))
        return [Product._row(r) for r in cursor.fetchall()]

    # ── WRITE ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create(mysql, name, price, category, image, description, stock=0):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO products (name, price, category, image, description, stock) VALUES (%s,%s,%s,%s,%s,%s)",
                (name, price, category, image, description, stock)
            )
            mysql.connection.commit()
            return cursor.lastrowid, None
        except Exception as e:
            mysql.connection.rollback()
            return None, str(e)

    @staticmethod
    def update(mysql, product_id, name, price, category, image, description, stock=None):
        cursor = mysql.connection.cursor()
        try:
            if stock is not None:
                cursor.execute(
                    """UPDATE products
                       SET name=%s, price=%s, category=%s, image=%s, description=%s, stock=%s
                       WHERE id=%s""",
                    (name, price, category, image, description, stock, product_id)
                )
            else:
                cursor.execute(
                    """UPDATE products
                       SET name=%s, price=%s, category=%s, image=%s, description=%s
                       WHERE id=%s""",
                    (name, price, category, image, description, product_id)
                )
            mysql.connection.commit()
            return True, None
        except Exception as e:
            mysql.connection.rollback()
            return False, str(e)

    @staticmethod
    def reserve_stock(mysql, product_id, qty):
        """Reserve qty units — called when an order is placed.
        Returns False if not enough available stock."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE products
            SET reserved = reserved + %s
            WHERE id = %s AND (stock - reserved) >= %s
        """, (qty, product_id, qty))
        mysql.connection.commit()
        return cursor.rowcount > 0

    @staticmethod
    def release_reservation(mysql, product_id, qty):
        """Release a reservation without deducting stock — called on cancellation/rejection."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE products
            SET reserved = GREATEST(0, reserved - %s)
            WHERE id = %s
        """, (qty, product_id))
        mysql.connection.commit()

    @staticmethod
    def confirm_deduction(mysql, product_id, qty):
        """Convert a reservation into a real deduction — called on payment approval or COD delivery.
        Decreases both stock and reserved."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE products
            SET stock = GREATEST(0, stock - %s),
                reserved = GREATEST(0, reserved - %s)
            WHERE id = %s
        """, (qty, qty, product_id))
        mysql.connection.commit()

    @staticmethod
    def update_stock(mysql, product_id, new_stock):
        """Admin manually sets absolute stock quantity."""
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE products SET stock=%s WHERE id=%s", (new_stock, product_id))
        mysql.connection.commit()

    @staticmethod
    def delete(mysql, product_id):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    # ── HELPER ────────────────────────────────────────────────────────────────

    @staticmethod
    def _row(r):
        stock    = r[6] if len(r) > 6 else 0
        reserved = r[7] if len(r) > 7 else 0
        available = max(0, stock - reserved)
        return {
            "id": r[0], "name": r[1], "price": r[2],
            "category": r[3], "image": r[4], "description": r[5],
            "stock": stock, "reserved": reserved, "available": available
        }