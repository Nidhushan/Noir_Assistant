import httpx
from app.db.database import create_conversation, save_message


async def process_message(message: str, conversation_id: int | None = None):
    if conversation_id is None:
        conversation_id = create_conversation(message[:50])

    save_message(conversation_id, "user", message)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "mlx-community/Qwen3-0.6B-4bit",
                "messages": [
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7,
                "max_tokens": 256
            }
        )

        response.raise_for_status()
        data = response.json()

    reply = data["choices"][0]["message"]["content"].strip()

    save_message(conversation_id, "assistant", reply)

    return conversation_id, reply