from werkzeug.security import generate_password_hash, check_password_hash


class Admin:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(256) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        mysql.connection.commit()

    @staticmethod
    def create(mysql, username, email, password):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
            INSERT INTO admin_users (username, email, password_hash)
            VALUES (%s, %s, %s)
            """, (username, email, generate_password_hash(password)))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def verify(mysql, username, password):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, username, email, password_hash
        FROM admin_users WHERE username = %s
        """, (username,))
        row = cursor.fetchone()
        if row and check_password_hash(row[3], password):
            return {"id": row[0], "username": row[1], "email": row[2]}
        return None

    @staticmethod
    def exists(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM admin_users")
        return cursor.fetchone()[0] > 0
