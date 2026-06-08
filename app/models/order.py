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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Safe upgrades for existing tables
        for sql in [
            "ALTER TABLE orders ADD COLUMN items_json TEXT AFTER total_price",
            "ALTER TABLE orders ADD COLUMN user_id INT NOT NULL DEFAULT 0 AFTER id",
        ]:
            try:
                cursor.execute(sql)
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()
        mysql.connection.commit()

    @staticmethod
    def create(mysql, order_data):
        cursor = mysql.connection.cursor()
        items_json = json.dumps(order_data.get("items", []))
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
            order_data["payment"],
            order_data["total"],
            items_json
        ))
        order_id = cursor.lastrowid
        mysql.connection.commit()
        return order_id

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
            "created_at":     row[14],
        }

    @staticmethod
    def get_all_by_user(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, user_id, customer_name, phone, province, district,
               city, area, address, landmark,
               payment_method, total_price, items_json,
               order_status, created_at
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
               order_status, created_at
        FROM orders WHERE id = %s
        """, (order_id,))
        row = cursor.fetchone()
        return Order._row_to_dict(row) if row else None

    @staticmethod
    def cancel(mysql, order_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE orders
            SET order_status = 'Cancelled'
            WHERE id = %s AND order_status = 'Pending'
        """, (order_id,))
        mysql.connection.commit()
        return cursor.rowcount
