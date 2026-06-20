import pymysql
import config


class Database:

    def __init__(self):
        try:
            print("Connecting to database...")

            self.__connection = pymysql.connect(
                host=config.MYSQL_HOST,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                database=config.MYSQL_DATABASE,
                cursorclass=pymysql.cursors.DictCursor
            )

            print(" Database connected successfully!")

        except Exception as e:
            print(" Database connection failed!")
            print("Error:", e)

    # ---------------- FETCH ONE ----------------
    def fetch_one(self, query, params=None):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result

    # ---------------- FETCH ALL ----------------
    def fetch_all(self, query, params=None):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results

    # ---------------- EXECUTE ----------------
    def execute(self, query, params=None):
        cursor = self.__connection.cursor()
        cursor.execute(query, params)
        self.__connection.commit()
        cursor.close()

    # ---------------- CLOSE ----------------
    def close(self):
        if self.__connection:
            self.__connection.close()

    # ---------------- CREATE TABLES ----------------
    @staticmethod
    def create_tables():
        print("🔧 Creating tables...")

        db = Database()

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                reset_token VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

 

        db.close()
