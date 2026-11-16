import httpx
from app.db.database import (
    create_conversation,
    save_message,
    get_messages,
    update_message_status
)

async def process_message(message: str, conversation_id: int | None = None):
    if conversation_id is None:
        conversation_id = create_conversation(message[:50])

    user_message_id = save_message(
        conversation_id,
        "user",
        message,
        status="pending"
    )

    history = get_messages(conversation_id)

    messages = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-10:]
    ]

    messages.insert(0, {
        "role": "system",
        "content": """
    You are Noir, a personal AI assistant.

    Your behaviour:
    - Communicate naturally, clearly, and concisely.
    - Answer the user's actual question directly.
    - Use previous conversation messages when relevant.
    - Remember information explicitly stated earlier in the conversation.
    - Never invent personal information or claim certainty without evidence.
    - Ask for clarification when necessary.
    - Avoid unnecessary repetition and excessive enthusiasm.
    """
    })

    print("Messages sent to LLM:", messages)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:8000/v1/chat/completions",
                json={
                    "model": "mlx-community/Qwen3-0.6B-4bit",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024
                }
            )
            response.raise_for_status()
            data = response.json()

    except httpx.ConnectError as exc:
        update_message_status(
            user_message_id, "failed", "503", str(exc)
        )
        raise

    except httpx.TimeoutException as exc:
        update_message_status(
            user_message_id, "failed", "504", str(exc)
        )
        raise

    except httpx.HTTPStatusError as exc:
        update_message_status(
            user_message_id, "failed", "502", str(exc)
        )
        raise

    except httpx.RequestError as exc:
        update_message_status(
            user_message_id, "failed", "502", str(exc)
        )
        raise

    reply = data["choices"][0]["message"]["content"].strip()

    if "<think>" in reply:
        if "</think>" in reply:
            reply = reply.split("</think>", 1)[1].strip()
        else:
            reply = "I couldn't complete that response. Please try again."

    save_message(conversation_id, "assistant", reply)

    return conversation_id, reply