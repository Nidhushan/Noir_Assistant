import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "noir.db"

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    connection = get_connection()
    connection.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                ON DELETE CASCADE
        )
    """)

    # Add generation status and error details to existing databases.
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(messages)")
    }

    if "status" not in columns:
        connection.execute("""
            ALTER TABLE messages
            ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'
        """)

    if "error_code" not in columns:
        connection.execute("""
            ALTER TABLE messages
            ADD COLUMN error_code TEXT
        """)

    if "error_detail" not in columns:
        connection.execute("""
            ALTER TABLE messages
            ADD COLUMN error_detail TEXT
        """)

    connection.commit()
    connection.close()

def create_conversation(title: str) -> int:
    connection = get_connection()

    cursor = connection.execute(
        "INSERT INTO conversations (title) VALUES (?)",
        (title,)
    )

    connection.commit()

    conversation_id = cursor.lastrowid

    connection.close()

    return conversation_id

def save_message(
    conversation_id: int,
    role: str,
    content: str,
    status: str = "completed"
) -> int:
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO messages (conversation_id, role, content, status)
        VALUES (?, ?, ?, ?)
        """,
        (conversation_id, role, content, status)
    )

    connection.execute(
        """
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (conversation_id,)
    )

    connection.commit()

    message_id = cursor.lastrowid

    connection.close()

    return message_id

def update_message_status(
    message_id: int,
    status: str,
    error_code: str | None = None,
    error_detail: str | None = None
):
    connection = get_connection()

    connection.execute(
        """
        UPDATE messages
        SET status = ?, error_code = ?, error_detail = ?
        WHERE id = ?
        """,
        (status, error_code, error_detail, message_id)
    )

    connection.commit()
    connection.close()

def get_messages(conversation_id: int) -> list:
    connection = get_connection()

    cursor = connection.execute(
        """
        SELECT id, role, content, created_at, status, error_code, error_detail
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    )

    messages = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return messages

def get_conversation(conversation_id: int) -> dict | None:
    connection = get_connection()

    cursor = connection.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,)
    )

    conversation = cursor.fetchone()

    connection.close()

    return dict(conversation) if conversation else None

def get_all_conversations():
    connection = get_connection()

    cursor = connection.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
        """
    )

    conversations = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return conversations