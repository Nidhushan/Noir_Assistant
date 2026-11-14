from app.db.database import create_conversation, save_message


def process_message(message: str, conversation_id: int | None = None):
    if conversation_id is None:
        conversation_id = create_conversation(message[:50])

    save_message(conversation_id, "user", message)

    reply = f"You said: {message}"

    save_message(conversation_id, "assistant", reply)

    return conversation_id, reply