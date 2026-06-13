import json

class Order:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            customer_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            province VARCHAR(50) NOT NULL,
            district VARCHAR(50) NOT NULL,
            city VARCHAR(50) NOT NULL,
            area VARCHAR(50) NOT NULL,
            address TEXT NOT NULL,
            landmark VARCHAR(100),
            payment_method VARCHAR(20) NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            items_json TEXT,
            order_status VARCHAR(20) DEFAULT 'Pending',
            payment_status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Safe upgrades for existing tables
        for sql in [
            "ALTER TABLE orders ADD COLUMN items_json TEXT AFTER total_price",
            "ALTER TABLE orders ADD COLUMN user_id INT NOT NULL DEFAULT 0 AFTER id",
            "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(20) DEFAULT 'Pending'",
            "ALTER TABLE orders ADD COLUMN transaction_code VARCHAR(100) DEFAULT NULL",
        ]:
            try:
                cursor.execute(sql)
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()
        mysql.connection.commit()

    @staticmethod
    def create(mysql, order_data):
        """Create order and reserve stock for all items.
        Returns (order_id, failed_items).
        failed_items is a list of product names that had insufficient stock.
        """
        from app.models.product import Product

        items     = order_data.get("items", [])
        payment   = order_data["payment"]

        # Try to reserve stock for every item first
        failed_items = []
        reserved_so_far = []
        for item in items:
            pid = item["id"]
            qty = item["qty"]
            ok  = Product.reserve_stock(mysql, pid, qty)
            if ok:
                reserved_so_far.append((pid, qty))
            else:
                failed_items.append(item["name"])

        # If any item failed, roll back all reservations made so far
        if failed_items:
            for pid, qty in reserved_so_far:
                Product.release_reservation(mysql, pid, qty)
            return None, failed_items

        # All reserved — create the order
        cursor     = mysql.connection.cursor()
        items_json = json.dumps(items)
        cursor.execute("""
        INSERT INTO orders (
            user_id, customer_name, phone, province, district,
            city, area, address, landmark,
            payment_method, total_price, items_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order_data["user_id"],
            order_data["name"],
            order_data["phone"],
            order_data["province"],
            order_data["district"],
            order_data["city"],
            order_data["area"],
            order_data["address"],
            order_data.get("landmark", ""),
            payment,
            order_data["total"],
            items_json
        ))
        order_id = cursor.lastrowid
        mysql.connection.commit()
        return order_id, []

    @staticmethod
    def _row_to_dict(row):
        items = []
        try:
            if row[12]:
                items = json.loads(row[12])
        except Exception:
            items = []
        return {
            "id":             row[0],
            "user_id":        row[1],
            "customer_name":  row[2],
            "phone":          row[3],
            "province":       row[4],
            "district":       row[5],
            "city":           row[6],
            "area":           row[7],
            "address":        row[8],
            "landmark":       row[9],
            "payment_method": row[10],
            "total_price":    row[11],
            "order_items":    items,
            "order_status":   row[13],
            "payment_status": row[14] if len(row) > 14 else "Pending",
            "created_at":     row[15] if len(row) > 15 else row[14],
        }

    @staticmethod
    def get_all_by_user(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, user_id, customer_name, phone, province, district,
               city, area, address, landmark,
               payment_method, total_price, items_json,
               order_status, payment_status, created_at
        FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC
        """, (user_id,))
        return [Order._row_to_dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(mysql, order_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, user_id, customer_name, phone, province, district,
               city, area, address, landmark,
               payment_method, total_price, items_json,
               order_status, payment_status, created_at
        FROM orders WHERE id = %s
        """, (order_id,))
        row = cursor.fetchone()
        return Order._row_to_dict(row) if row else None

    @staticmethod
    def cancel(mysql, order_id, user_id):
        """Cancel order and release stock reservations."""
        from app.models.product import Product

        order = Order.get_by_id(mysql, order_id)
        if not order or order["user_id"] != user_id:
            return False
        if order["order_status"] not in ("Pending",):
            return False

        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE orders
            SET order_status = 'Cancelled'
            WHERE id = %s AND order_status = 'Pending' AND user_id = %s
        """, (order_id, user_id))
        mysql.connection.commit()

        if cursor.rowcount:
            # Release reservations
            for item in order.get("order_items", []):
                Product.release_reservation(mysql, item["id"], item["qty"])
            return True
        return False

    @staticmethod
    def confirm_stock(mysql, order_id):
        """Convert reservations to real deductions — call on payment approval or COD delivery."""
        from app.models.product import Product

        order = Order.get_by_id(mysql, order_id)
        if not order:
            return
        for item in order.get("order_items", []):
            Product.confirm_deduction(mysql, item["id"], item["qty"])

    @staticmethod
    def release_stock(mysql, order_id):
        """Release reservations without deducting — call on payment rejection."""
        from app.models.product import Product

        order = Order.get_by_id(mysql, order_id)
        if not order:
            return
        for item in order.get("order_items", []):
            Product.release_reservation(mysql, item["id"], item["qty"])