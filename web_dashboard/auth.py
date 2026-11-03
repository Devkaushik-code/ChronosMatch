import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "users.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_auth_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def create_user(username, email, password):
    username = username.strip()
    email = email.strip().lower()

    if len(username) < 3 or len(username) > 30:
        return False, "Username must contain 3 to 30 characters."

    if not username.replace("_", "").isalnum():
        return False, "Username can contain only letters, numbers and underscores."

    if len(email) > 254 or "@" not in email or email.startswith("@"):
        return False, "Enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if len(password) > 128:
        return False, "Password is too long."

    password_hash = generate_password_hash(password)

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (username, email, password_hash),
            )

        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "Username or email is already registered."


def authenticate_user(email, password):
    email = email.strip().lower()

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT id, username, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if user is None:
        return None

    if not check_password_hash(user["password_hash"], password):
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
    }


def get_user_by_id(user_id):
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT id, username, email
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if user is None:
        return None

    return dict(user)


initialize_auth_database()
