import httpx
import logging
from app.db.database import (
    create_conversation,
    save_message,
    get_messages,
    update_message_status
)
from app.config import (
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT
)

logger = logging.getLogger(__name__)

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

    logger.info("Sending request to model: %s", LLM_MODEL)

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "temperature": LLM_TEMPERATURE,
                    "max_tokens": LLM_MAX_TOKENS
                }
            )
            response.raise_for_status()
            data = response.json()

    except httpx.ConnectError as exc:
        logger.warning("Local model connection failed: %s", exc)
        update_message_status(
            user_message_id, "failed", "503", str(exc)
        )
        raise

    except httpx.TimeoutException as exc:
        logger.warning("Local model request timed out: %s", exc)
        update_message_status(
            user_message_id, "failed", "504", str(exc)
        )
        raise

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Local model returned HTTP %s: %s",
            exc.response.status_code,
            exc
        )
        update_message_status(
            user_message_id, "failed", "502", str(exc)
        )
        raise

    except httpx.RequestError as exc:
        logger.error("Local model request failed: %s", exc)
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