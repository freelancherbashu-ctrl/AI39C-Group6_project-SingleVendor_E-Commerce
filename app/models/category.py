class Category:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(80) NOT NULL UNIQUE,
            image VARCHAR(255) NOT NULL DEFAULT 'images/placeholder.png',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        mysql.connection.commit()

    @staticmethod
    def seed(mysql):
        """Insert default categories only when the table is empty."""
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] > 0:
            return
        defaults = [
            ("electronics", "images/electronics.png"),
            ("clothes",     "images/clothes.svg"),
            ("shoes",       "images/shoes.svg"),
        ]
        cursor.executemany("INSERT INTO categories (name, image) VALUES (%s,%s)", defaults)
        mysql.connection.commit()

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_all(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, image FROM categories ORDER BY id")
        return [Category._row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_by_id(mysql, cat_id):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, image FROM categories WHERE id=%s", (cat_id,))
        row = cursor.fetchone()
        return Category._row(row) if row else None

    @staticmethod
    def get_by_name(mysql, name):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, image FROM categories WHERE name=%s", (name,))
        row = cursor.fetchone()
        return Category._row(row) if row else None

    # ── WRITE ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create(mysql, name, image):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO categories (name, image) VALUES (%s,%s)",
                (name.lower().strip(), image)
            )
            mysql.connection.commit()
            return cursor.lastrowid, None
        except Exception as e:
            mysql.connection.rollback()
            return None, str(e)

    @staticmethod
    def update(mysql, cat_id, name, image):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "UPDATE categories SET name=%s, image=%s WHERE id=%s",
                (name.lower().strip(), image, cat_id)
            )
            mysql.connection.commit()
            return True, None
        except Exception as e:
            mysql.connection.rollback()
            return False, str(e)

    @staticmethod
    def delete(mysql, cat_id):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("DELETE FROM categories WHERE id=%s", (cat_id,))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    # ── HELPER ────────────────────────────────────────────────────────────────

    @staticmethod
    def _row(r):
        return {"id": r[0], "name": r[1], "image": r[2]}