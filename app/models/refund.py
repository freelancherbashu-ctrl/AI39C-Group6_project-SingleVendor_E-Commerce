class Refund:

    VALID_STATUSES = ("Pending", "Approved", "Rejected", "Completed")

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            user_id INT NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Pending',
            admin_note TEXT DEFAULT NULL,
            refund_amount DECIMAL(10,2) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY one_refund_per_order (order_id)
        )
        """)
        mysql.connection.commit()

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _row(row):
        return {
            "id":            row[0],
            "order_id":      row[1],
            "user_id":       row[2],
            "reason":        row[3],
            "status":        row[4],
            "admin_note":    row[5],
            "refund_amount": row[6],
            "created_at":    row[7],
            "updated_at":    row[8],
        }

    @staticmethod
    def get_by_order(mysql, order_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, order_id, user_id, reason, status,
                   admin_note, refund_amount, created_at, updated_at
            FROM refunds WHERE order_id = %s
        """, (order_id,))
        row = cursor.fetchone()
        return Refund._row(row) if row else None

    @staticmethod
    def get_by_user(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT r.id, r.order_id, r.user_id, r.reason, r.status,
                   r.admin_note, r.refund_amount, r.created_at, r.updated_at,
                   o.total_price, o.created_at AS order_date
            FROM refunds r
            JOIN orders o ON o.id = r.order_id
            WHERE r.user_id = %s
            ORDER BY r.created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = Refund._row(row)
            d["order_total"] = row[9]
            d["order_date"]  = row[10]
            result.append(d)
        return result

    @staticmethod
    def get_all_admin(mysql, status=None):
        cursor = mysql.connection.cursor()
        if status:
            cursor.execute("""
                SELECT r.id, r.order_id, r.user_id, r.reason, r.status,
                       r.admin_note, r.refund_amount, r.created_at, r.updated_at,
                       u.full_name, u.email, o.total_price
                FROM refunds r
                JOIN users u ON u.id = r.user_id
                JOIN orders o ON o.id = r.order_id
                WHERE r.status = %s
                ORDER BY r.created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT r.id, r.order_id, r.user_id, r.reason, r.status,
                       r.admin_note, r.refund_amount, r.created_at, r.updated_at,
                       u.full_name, u.email, o.total_price
                FROM refunds r
                JOIN users u ON u.id = r.user_id
                JOIN orders o ON o.id = r.order_id
                ORDER BY r.created_at DESC
            """)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = Refund._row(row)
            d["user_name"]   = row[9]
            d["user_email"]  = row[10]
            d["order_total"] = row[11]
            result.append(d)
        return result

    @staticmethod
    def get_by_id(mysql, refund_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT r.id, r.order_id, r.user_id, r.reason, r.status,
                   r.admin_note, r.refund_amount, r.created_at, r.updated_at,
                   u.full_name, u.email, o.total_price, o.payment_method
            FROM refunds r
            JOIN users u ON u.id = r.user_id
            JOIN orders o ON o.id = r.order_id
            WHERE r.id = %s
        """, (refund_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = Refund._row(row)
        d["user_name"]      = row[9]
        d["user_email"]     = row[10]
        d["order_total"]    = row[11]
        d["payment_method"] = row[12]
        return d

    # ── WRITE ─────────────────────────────────────────────────────────────────

    @staticmethod
    def request(mysql, order_id, user_id, reason):
        """User submits a refund request. Returns (True, None) or (False, msg)."""
        from app.models.order import Order
        order = Order.get_by_id(mysql, order_id)
        if not order or order["user_id"] != user_id:
            return False, "Order not found."
        if order["order_status"] not in ("Completed",):
            return False, "Refunds can only be requested for completed orders."
        if Refund.get_by_order(mysql, order_id):
            return False, "A refund request already exists for this order."
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO refunds (order_id, user_id, reason, refund_amount)
                VALUES (%s, %s, %s, %s)
            """, (order_id, user_id, reason.strip(), order["total_price"]))
            mysql.connection.commit()
            return True, None
        except Exception as e:
            mysql.connection.rollback()
            return False, str(e)

    @staticmethod
    def update_status(mysql, refund_id, status, admin_note=None):
        """Admin approves/rejects a refund. Returns True on success."""
        if status not in Refund.VALID_STATUSES:
            return False
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                UPDATE refunds
                SET status=%s, admin_note=%s
                WHERE id=%s
            """, (status, admin_note, refund_id))
            mysql.connection.commit()
            return cursor.rowcount > 0
        except Exception:
            mysql.connection.rollback()
            return False
