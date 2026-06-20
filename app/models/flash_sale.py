from datetime import datetime


class FlashSale:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS flash_sales (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            product_id  INT NOT NULL,
            discount    DECIMAL(5,2) NOT NULL,
            sale_price  INT NOT NULL,
            starts_at   DATETIME NOT NULL,
            ends_at     DATETIME NOT NULL,
            label       VARCHAR(80) DEFAULT 'Flash Sale',
            is_active   TINYINT(1) DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
        """)
        mysql.connection.commit()

    @staticmethod
    def _parse_dt(s):
        """Normalize datetime-local input (2026-06-10T14:30) to MySQL format."""
        if s:
            return s.replace("T", " ")
        return s

    # ── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_sale_map(mysql):
        """Return {product_id: {sale_price, discount, label}} for all active sales."""
        active = FlashSale.get_active(mysql)
        return {
            s["product_id"]: {
                "sale_price": s["sale_price"],
                "discount":   s["discount"],
                "label":      s["label"],
            }
            for s in active
        }

    @staticmethod
    def get_active(mysql):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT fs.id, fs.product_id, fs.discount, fs.sale_price,
                   fs.starts_at, fs.ends_at, fs.label, fs.is_active,
                   p.name, p.image, p.price
            FROM flash_sales fs
            JOIN products p ON p.id = fs.product_id
            WHERE fs.is_active = 1
              AND fs.starts_at <= %s
              AND fs.ends_at   >= %s
            ORDER BY fs.ends_at ASC
        """, (now, now))
        return [FlashSale._row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_all(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT fs.id, fs.product_id, fs.discount, fs.sale_price,
                   fs.starts_at, fs.ends_at, fs.label, fs.is_active,
                   p.name, p.image, p.price
            FROM flash_sales fs
            JOIN products p ON p.id = fs.product_id
            ORDER BY fs.id DESC
        """)
        return [FlashSale._row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_by_id(mysql, sale_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT fs.id, fs.product_id, fs.discount, fs.sale_price,
                   fs.starts_at, fs.ends_at, fs.label, fs.is_active,
                   p.name, p.image, p.price
            FROM flash_sales fs
            JOIN products p ON p.id = fs.product_id
            WHERE fs.id = %s
        """, (sale_id,))
        row = cursor.fetchone()
        return FlashSale._row(row) if row else None

    # ── WRITE ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create(mysql, product_id, discount, starts_at, ends_at, label):
        try:
            cur1 = mysql.connection.cursor()
            cur1.execute("SELECT price FROM products WHERE id=%s", (int(product_id),))
            row = cur1.fetchone()
            if not row:
                return None, "Product not found"
            original   = int(row[0])
            sale_price = round(original * (1 - float(discount) / 100))
            starts_at  = FlashSale._parse_dt(starts_at)
            ends_at    = FlashSale._parse_dt(ends_at)
            cur2 = mysql.connection.cursor()
            cur2.execute("""
                INSERT INTO flash_sales
                    (product_id, discount, sale_price, starts_at, ends_at, label)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (int(product_id), float(discount), sale_price, starts_at, ends_at, label))
            mysql.connection.commit()
            return cur2.lastrowid, None
        except Exception as e:
            mysql.connection.rollback()
            return None, str(e)

    @staticmethod
    def update(mysql, sale_id, product_id, discount, starts_at, ends_at, label, is_active):
        try:
            cur1 = mysql.connection.cursor()
            cur1.execute("SELECT price FROM products WHERE id=%s", (int(product_id),))
            row = cur1.fetchone()
            if not row:
                return False, "Product not found"
            original   = int(row[0])
            sale_price = round(original * (1 - float(discount) / 100))
            starts_at  = FlashSale._parse_dt(starts_at)
            ends_at    = FlashSale._parse_dt(ends_at)
            cur2 = mysql.connection.cursor()
            cur2.execute("""
                UPDATE flash_sales
                SET product_id=%s, discount=%s, sale_price=%s,
                    starts_at=%s, ends_at=%s, label=%s, is_active=%s
                WHERE id=%s
            """, (int(product_id), float(discount), sale_price, starts_at, ends_at, label, int(is_active), int(sale_id)))
            mysql.connection.commit()
            return True, None
        except Exception as e:
            mysql.connection.rollback()
            return False, str(e)

    @staticmethod
    def delete(mysql, sale_id):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("DELETE FROM flash_sales WHERE id=%s", (sale_id,))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def toggle_active(mysql, sale_id):
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE flash_sales SET is_active = NOT is_active WHERE id=%s", (sale_id,)
        )
        mysql.connection.commit()

    # ── HELPER ────────────────────────────────────────────────────────────────

    @staticmethod
    def _row(r):
        return {
            "id":             r[0],
            "product_id":     r[1],
            "discount":       float(r[2]),
            "sale_price":     r[3],
            "starts_at":      r[4],
            "ends_at":        r[5],
            "label":          r[6],
            "is_active":      bool(r[7]),
            "product_name":   r[8],
            "product_image":  r[9],
            "original_price": r[10],
        }