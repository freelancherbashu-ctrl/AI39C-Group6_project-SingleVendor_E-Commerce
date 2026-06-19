from app.models.database import get_db


class CartItem:
    """Persisted cart stored in the database per customer."""

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cart_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_customer_product (customer_id, product_id),
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )
        db.commit()
        cursor.close()

    @staticmethod
    def get_cart(customer_id):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT ci.id, ci.quantity, p.id AS product_id,
                   p.name, p.price, p.image_url, p.stock,
                   (ci.quantity * p.price) AS line_total
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            WHERE ci.customer_id = %s
            ORDER BY ci.added_at
            """,
            (customer_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows

    @staticmethod
    def add_or_update(customer_id, product_id, quantity):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO cart_items (customer_id, product_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
            """,
            (customer_id, product_id, quantity),
        )
        db.commit()
        cursor.close()

    @staticmethod
    def update_quantity(customer_id, product_id, quantity):
        db = get_db()
        cursor = db.cursor()
        if quantity <= 0:
            cursor.execute(
                "DELETE FROM cart_items WHERE customer_id=%s AND product_id=%s",
                (customer_id, product_id),
            )
        else:
            cursor.execute(
                "UPDATE cart_items SET quantity=%s WHERE customer_id=%s AND product_id=%s",
                (quantity, customer_id, product_id),
            )
        db.commit()
        cursor.close()

    @staticmethod
    def remove(customer_id, product_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM cart_items WHERE customer_id=%s AND product_id=%s",
            (customer_id, product_id),
        )
        db.commit()
        cursor.close()

    @staticmethod
    def clear(customer_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM cart_items WHERE customer_id=%s", (customer_id,))
        db.commit()
        cursor.close()

    @staticmethod
    def count(customer_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM cart_items WHERE customer_id=%s",
            (customer_id,),
        )
        total = cursor.fetchone()[0]
        cursor.close()
        return int(total)
