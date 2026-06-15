from datetime import datetime


class Coupon:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(30) NOT NULL UNIQUE,
            discount_type ENUM('percent','fixed') NOT NULL DEFAULT 'percent',
            discount_value DECIMAL(10,2) NOT NULL,
            min_order_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            max_uses INT DEFAULT NULL,
            used_count INT NOT NULL DEFAULT 0,
            valid_from DATETIME NOT NULL,
            valid_until DATETIME NOT NULL,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Track per-user usage to prevent reuse
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupon_uses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            coupon_id INT NOT NULL,
            user_id INT NOT NULL,
            order_id INT DEFAULT NULL,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY one_use_per_user (coupon_id, user_id)
        )
        """)
        mysql.connection.commit()

    # ── VALIDATE ──────────────────────────────────────────────────────────────

    @staticmethod
    def validate(mysql, code, user_id, cart_total):
        """
        Returns (coupon_dict, None) on success
        or (None, error_message) on failure.
        """
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, code, discount_type, discount_value,
                   min_order_amount, max_uses, used_count,
                   valid_from, valid_until, is_active
            FROM coupons WHERE code = %s
        """, (code.strip().upper(),))
        row = cursor.fetchone()

        if not row:
            return None, "Invalid coupon code."

        coupon = {
            "id": row[0], "code": row[1], "discount_type": row[2],
            "discount_value": float(row[3]), "min_order_amount": float(row[4]),
            "max_uses": row[5], "used_count": row[6],
            "valid_from": row[7], "valid_until": row[8], "is_active": row[9],
        }

        if not coupon["is_active"]:
            return None, "This coupon is no longer active."

        now = datetime.now()
        if now < coupon["valid_from"]:
            return None, "This coupon is not yet valid."
        if now > coupon["valid_until"]:
            return None, "This coupon has expired."

        if coupon["max_uses"] is not None and coupon["used_count"] >= coupon["max_uses"]:
            return None, "This coupon has reached its usage limit."

        if cart_total < coupon["min_order_amount"]:
            return None, f"Minimum order of Rs. {coupon['min_order_amount']:,.0f} required for this coupon."

        # Check if user already used this coupon
        cursor.execute("""
            SELECT id FROM coupon_uses WHERE coupon_id=%s AND user_id=%s
        """, (coupon["id"], user_id))
        if cursor.fetchone():
            return None, "You have already used this coupon."

        coupon["discount_amount"] = Coupon.calc_discount(coupon, cart_total)
        return coupon, None

    @staticmethod
    def calc_discount(coupon, cart_total):
        if coupon["discount_type"] == "percent":
            return round(cart_total * coupon["discount_value"] / 100, 2)
        else:
            return min(coupon["discount_value"], cart_total)

    @staticmethod
    def apply(mysql, coupon_id, user_id, order_id):
        """Mark coupon as used by this user for this order."""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO coupon_uses (coupon_id, user_id, order_id)
                VALUES (%s, %s, %s)
            """, (coupon_id, user_id, order_id))
            cursor.execute("""
                UPDATE coupons SET used_count = used_count + 1 WHERE id = %s
            """, (coupon_id,))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_all(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, code, discount_type, discount_value, min_order_amount,
                   max_uses, used_count, valid_from, valid_until, is_active, created_at
            FROM coupons ORDER BY created_at DESC
        """)
        return [Coupon._row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_by_id(mysql, coupon_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, code, discount_type, discount_value, min_order_amount,
                   max_uses, used_count, valid_from, valid_until, is_active, created_at
            FROM coupons WHERE id = %s
        """, (coupon_id,))
        row = cursor.fetchone()
        return Coupon._row(row) if row else None

    @staticmethod
    def _row(r):
        return {
            "id": r[0], "code": r[1], "discount_type": r[2],
            "discount_value": float(r[3]), "min_order_amount": float(r[4]),
            "max_uses": r[5], "used_count": r[6],
            "valid_from": r[7], "valid_until": r[8],
            "is_active": bool(r[9]), "created_at": r[10],
        }

    # ── WRITE ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create(mysql, code, discount_type, discount_value,
               min_order_amount, max_uses, valid_from, valid_until):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO coupons
                    (code, discount_type, discount_value, min_order_amount,
                     max_uses, valid_from, valid_until)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (code.strip().upper(), discount_type, discount_value,
                  min_order_amount, max_uses or None, valid_from, valid_until))
            mysql.connection.commit()
            return True, None
        except Exception as e:
            mysql.connection.rollback()
            err = str(e)
            if "Duplicate" in err:
                return False, "A coupon with that code already exists."
            return False, err

    @staticmethod
    def update(mysql, coupon_id, code, discount_type, discount_value,
               min_order_amount, max_uses, valid_from, valid_until, is_active):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                UPDATE coupons
                SET code=%s, discount_type=%s, discount_value=%s,
                    min_order_amount=%s, max_uses=%s,
                    valid_from=%s, valid_until=%s, is_active=%s
                WHERE id=%s
            """, (code.strip().upper(), discount_type, discount_value,
                  min_order_amount, max_uses or None,
                  valid_from, valid_until, int(is_active), coupon_id))
            mysql.connection.commit()
            return True, None
        except Exception as e:
            mysql.connection.rollback()
            return False, str(e)

    @staticmethod
    def delete(mysql, coupon_id):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("DELETE FROM coupons WHERE id=%s", (coupon_id,))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False
