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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        mysql.connection.commit()

    @staticmethod
    def seed(mysql):
        """Insert default products only when the table is empty."""
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] > 0:
            return
        defaults = [
            ("Laptop",      200000, "electronics", "/static/images/laptop.png",
             "A powerful laptop perfect for work, study, and gaming."),
            ("i-Phone",     100000, "electronics", "/static/images/iphone.png",
             "The latest iPhone with a stunning camera system."),
            ("Headphones",   3000,  "electronics", "/static/images/headphones.png",
             "Premium over-ear headphones with deep bass."),
            ("Hoodie",       2500,  "clothes",     "/static/images/hoodie.png",
             "A cozy and stylish hoodie made from soft fleece."),
            ("Jacket",       5000,  "clothes",     "/static/images/jacket.png",
             "A durable and trendy jacket for Nepal's changing weather."),
            ("Pizza",         900,  "food",        "/static/images/pizza.png",
             "Freshly baked pizza with crispy crust."),
        ]
        cursor.executemany(
            "INSERT INTO products (name, price, category, image, description) VALUES (%s,%s,%s,%s,%s)",
            defaults
        )
        mysql.connection.commit()

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_all(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, price, category, image, description FROM products ORDER BY id")
        rows = cursor.fetchall()
        return [Product._row(r) for r in rows]

    @staticmethod
    def get_by_id(mysql, product_id):
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, name, price, category, image, description FROM products WHERE id=%s",
            (product_id,)
        )
        row = cursor.fetchone()
        return Product._row(row) if row else None

    @staticmethod
    def get_by_category(mysql, category):
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, name, price, category, image, description FROM products WHERE category=%s ORDER BY id",
            (category,)
        )
        return [Product._row(r) for r in cursor.fetchall()]

    @staticmethod
    def search(mysql, query):
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, name, price, category, image, description FROM products WHERE name LIKE %s ORDER BY id",
            (f"%{query}%",)
        )
        return [Product._row(r) for r in cursor.fetchall()]

    # ── WRITE ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create(mysql, name, price, category, image, description):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO products (name, price, category, image, description) VALUES (%s,%s,%s,%s,%s)",
                (name, price, category, image, description)
            )
            mysql.connection.commit()
            return cursor.lastrowid, None
        except Exception as e:
            mysql.connection.rollback()
            return None, str(e)

    @staticmethod
    def update(mysql, product_id, name, price, category, image, description):
        cursor = mysql.connection.cursor()
        try:
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
        return {
            "id": r[0], "name": r[1], "price": r[2],
            "category": r[3], "image": r[4], "description": r[5]
        }
