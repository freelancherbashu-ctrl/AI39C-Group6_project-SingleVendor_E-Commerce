class Review:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            user_id INT NOT NULL,
            order_id INT NOT NULL,
            rating TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NULL DEFAULT NULL,
            UNIQUE KEY one_review_per_product (user_id, product_id)
        )
        """)
        mysql.connection.commit()
        # Safe upgrades for existing tables: one review per product (not per order),
        # editable instead of duplicated when the same product is bought again.
        for sql in [
            "ALTER TABLE reviews ADD COLUMN updated_at TIMESTAMP NULL DEFAULT NULL",
            "ALTER TABLE reviews DROP INDEX one_review_per_order_item",
            "ALTER TABLE reviews ADD UNIQUE KEY one_review_per_product (user_id, product_id)",
        ]:
            try:
                cursor.execute(sql)
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_for_product(mysql, product_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT r.id, r.rating, r.comment, r.created_at,
                   u.full_name, u.profile_picture, r.updated_at
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            WHERE r.product_id = %s
            ORDER BY r.created_at DESC
        """, (product_id,))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "rating": row[1],
                "comment": row[2],
                "created_at": row[3],
                "user_name": row[4],
                "user_picture": row[5],
                "updated_at": row[6] if len(row) > 6 else None,
            }
            for row in rows
        ]

    @staticmethod
    def get_avg_rating(mysql, product_id):
        """Returns (avg_rating, count). avg_rating is None when no reviews."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = %s
        """, (product_id,))
        row = cursor.fetchone()
        avg = round(float(row[0]), 1) if row[0] else None
        return avg, row[1]

    @staticmethod
    def get_avg_ratings_bulk(mysql, product_ids):
        """Returns dict {product_id: (avg, count)} for a list of IDs."""
        if not product_ids:
            return {}
        placeholders = ",".join(["%s"] * len(product_ids))
        cursor = mysql.connection.cursor()
        cursor.execute(f"""
            SELECT product_id, AVG(rating), COUNT(*)
            FROM reviews
            WHERE product_id IN ({placeholders})
            GROUP BY product_id
        """, product_ids)
        return {
            row[0]: (round(float(row[1]), 1), row[2])
            for row in cursor.fetchall()
        }

    @staticmethod
    def get_user_review_for_product(mysql, user_id, product_id):
        """Return this user's existing review for a product (for editing), or None."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, rating, comment, order_id
            FROM reviews WHERE user_id=%s AND product_id=%s
        """, (user_id, product_id))
        row = cursor.fetchone()
        if not row:
            return None
        return {"id": row[0], "rating": row[1], "comment": row[2], "order_id": row[3]}

    @staticmethod
    def can_review(mysql, user_id, product_id):
        """True if the user has at least one completed order containing this product.
        One review per product per user — buying it again doesn't grant a second review,
        it just lets you keep your existing one (or write your first one if you hadn't)."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT o.id FROM orders o
            WHERE o.user_id = %s
              AND o.order_status = 'Completed'
              AND JSON_CONTAINS(o.items_json, JSON_OBJECT('id', %s), '$')
            ORDER BY o.created_at DESC
            LIMIT 1
        """, (user_id, product_id))
        row = cursor.fetchone()
        return row[0] if row else None

    @staticmethod
    def get_reviewable_orders(mysql, user_id, product_id):
        """Return a qualifying completed order id for this user+product, or None
        if the user has never completed a purchase of it."""
        return Review.can_review(mysql, user_id, product_id)

    # ── WRITE ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create(mysql, user_id, product_id, order_id, rating, comment):
        """Returns (True, None) on success or (False, error_msg).
        Requires a completed order containing the product; fails if a review
        already exists (use Review.update to edit it instead)."""
        if Review.get_user_review_for_product(mysql, user_id, product_id):
            return False, "You've already reviewed this product. Edit your existing review instead."
        qualifying_order_id = order_id if order_id else Review.can_review(mysql, user_id, product_id)
        if not qualifying_order_id:
            return False, "You can only review products you've bought, once your order is completed."
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO reviews (product_id, user_id, order_id, rating, comment)
                VALUES (%s, %s, %s, %s, %s)
            """, (product_id, user_id, qualifying_order_id, rating, comment))
            mysql.connection.commit()
            return True, None
        except Exception as e:
            mysql.connection.rollback()
            return False, str(e)

    @staticmethod
    def update(mysql, review_id, user_id, rating, comment):
        """Edit your own existing review. Returns (True, None) or (False, error_msg)."""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                UPDATE reviews SET rating=%s, comment=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s
            """, (rating, comment, review_id, user_id))
            mysql.connection.commit()
            if cursor.rowcount:
                return True, None
            return False, "Review not found."
        except Exception as e:
            mysql.connection.rollback()
            return False, str(e)

    @staticmethod
    def delete(mysql, review_id):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("DELETE FROM reviews WHERE id=%s", (review_id,))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_all_admin(mysql, limit=100):
        """For admin moderation view."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT r.id, r.rating, r.comment, r.created_at,
                   u.full_name, p.name AS product_name, r.product_id, r.order_id
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            JOIN products p ON p.id = r.product_id
            ORDER BY r.created_at DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0], "rating": row[1], "comment": row[2],
                "created_at": row[3], "user_name": row[4],
                "product_name": row[5], "product_id": row[6], "order_id": row[7],
            }
            for row in rows
        ]
