class Wishlist:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishlists (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            product_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_wishlist (user_id, product_id)
        )
        """)
        mysql.connection.commit()

    @staticmethod
    def add(mysql, user_id, product_id):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
            INSERT INTO wishlists (user_id, product_id)
            VALUES (%s, %s)
            """, (user_id, product_id))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def remove(mysql, user_id, product_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        DELETE FROM wishlists
        WHERE user_id = %s AND product_id = %s
        """, (user_id, product_id))
        mysql.connection.commit()
        return cursor.rowcount > 0

    @staticmethod
    def is_wishlisted(mysql, user_id, product_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id FROM wishlists
        WHERE user_id = %s AND product_id = %s
        """, (user_id, product_id))
        return cursor.fetchone() is not None

    @staticmethod
    def get_product_ids(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT product_id FROM wishlists
        WHERE user_id = %s
        """, (user_id,))
        return {row[0] for row in cursor.fetchall()}

    @staticmethod
    def get_count(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT COUNT(*) FROM wishlists WHERE user_id = %s
        """, (user_id,))
        return cursor.fetchone()[0]