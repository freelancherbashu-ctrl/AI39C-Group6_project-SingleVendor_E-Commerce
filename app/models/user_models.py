from app.models.database import get_db


class Customer:
    """Represents a customer account and provides simple data
    access helpers for the customers table."""

    def __init__(self, id, full_name, email, phone, address, password_hash):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.phone = phone
        self.address = address
        self.password_hash = password_hash

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(120) NOT NULL,
                email VARCHAR(120) NOT NULL UNIQUE,
                phone VARCHAR(20),
                address VARCHAR(255),
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.commit()
        cursor.close()

    @staticmethod
    def find_by_email(email):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE email = %s", (email,))
        row = cursor.fetchone()
        cursor.close()
        return row

    @staticmethod
    def find_by_id(customer_id):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
        row = cursor.fetchone()
        cursor.close()
        return row

    @staticmethod
    def create(full_name, email, phone, address, password_hash):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO customers (full_name, email, phone, address, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (full_name, email, phone, address, password_hash),
        )
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id

    @staticmethod
    def update_profile(customer_id, full_name, phone, address):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            UPDATE customers
            SET full_name = %s, phone = %s, address = %s
            WHERE id = %s
            """,
            (full_name, phone, address, customer_id),
        )
        db.commit()
        cursor.close()
