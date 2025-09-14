from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
from mysql.connector import Error


def register_user(username, email, password):
    conn = get_db_connection()
    if conn is None:
        return False

    hashed_password = generate_password_hash(password)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       (username, email, hashed_password))
        conn.commit()
        return True
    except Error as e:
        if e.errno == 1062:  # Duplicate entry error
            print("Username or email already exists")
        else:
            print(f"Error registering user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def verify_user(username, password):
    conn = get_db_connection()
    if conn is None:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            return user
        return None
    except Error as e:
        print(f"Error verifying user: {e}")
        return None
    finally:
        cursor.close()
        conn.close()