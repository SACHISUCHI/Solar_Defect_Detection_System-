import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash 

DB_CONFIG = dict(
    host="localhost",
    user="root",        # <-- change if needed
    password="",        # <-- change if needed
    database="defect_detection",
)

def _connect():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    conn = None
    try:
        conn = _connect()
        if conn.is_connected():
            cursor = conn.cursor()

            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    user_type ENUM('admin','user') NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create uploads table (without assuming columns exist yet)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploads (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result TEXT,
                    action_taken VARCHAR(100),
                    action_notes TEXT,
                    action_date TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            # --- Ensure panel detail columns exist (idempotent) ---
            # MySQL 8 supports IF NOT EXISTS; for broader compatibility we try/except
            def add_col(sql):
                try:
                    cursor.execute(sql)
                except Error as e:
                    # 1060 = Duplicate column name -> already exists; ignore
                    if e.errno != 1060:
                        raise

            add_col("ALTER TABLE uploads ADD COLUMN panel_id VARCHAR(50)")
            add_col("ALTER TABLE uploads ADD COLUMN site_name VARCHAR(100)")
            add_col("ALTER TABLE uploads ADD COLUMN location VARCHAR(255)")
            add_col("ALTER TABLE uploads ADD COLUMN panel_notes TEXT")

            # Seed admin
            admin_password = generate_password_hash("admin123")
            try:
                cursor.execute(
                    "INSERT INTO users (username, email, password, user_type) VALUES (%s,%s,%s,%s)",
                    ("admin", "admin@solar.com", admin_password, "admin"),
                )
                print("Admin user created successfully")
            except Error as e:
                if e.errno == 1062:
                    print("Admin user already exists")
                else:
                    print(f"Error creating admin user: {e}")

            conn.commit()
            cursor.close()

    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

def get_db_connection():
    try:
        return _connect()
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None
