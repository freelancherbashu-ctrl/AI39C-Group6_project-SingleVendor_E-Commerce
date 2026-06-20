from app.models.database import get_db


class Product:
    """Represents a product in the store."""

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                stock INT NOT NULL DEFAULT 0,
                category VARCHAR(100),
                image_url VARCHAR(500),
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.commit()
        cursor.close()

    @staticmethod
    def get_all(category=None, search=None):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM products WHERE is_active = 1"
        params = []
        if category:
            query += " AND category = %s"
            params.append(category)
        if search:
            query += " AND (name LIKE %s OR description LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    @staticmethod
    def find_by_id(product_id):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        row = cursor.fetchone()
        cursor.close()
        return row

    @staticmethod
    def get_categories():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT DISTINCT category FROM products WHERE is_active = 1 AND category IS NOT NULL"
        )
        rows = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rows]

    @staticmethod
    def create(name, description, price, stock, category, image_url):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO products (name, description, price, stock, category, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (name, description, price, stock, category, image_url),
        )
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id

    @staticmethod
    def update(product_id, name, description, price, stock, category, image_url):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            UPDATE products
            SET name=%s, description=%s, price=%s, stock=%s, category=%s, image_url=%s
            WHERE id=%s
            """,
            (name, description, price, stock, category, image_url, product_id),
        )
        db.commit()
        cursor.close()

    @staticmethod
    def delete(product_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE products SET is_active = 0 WHERE id = %s", (product_id,))
        db.commit()
        cursor.close()

    @staticmethod
    def update_stock(product_id, quantity_change):
        """Reduce stock by quantity_change (pass negative to decrease)."""
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE products SET stock = stock + %s WHERE id = %s",
            (quantity_change, product_id),
        )
        db.commit()
        cursor.close()
