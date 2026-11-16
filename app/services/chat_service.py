import httpx
import logging
import json
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


class ThinkTagFilter:

    def __init__(self):
        self.inside_think = False
        self.buffer = ""

    def feed(self, text: str) -> str:

        self.buffer += text
        output = ""

        while self.buffer:

            if self.inside_think:
                closing_tag = "</think>"
                position = self.buffer.find(closing_tag)

                if position != -1:
                    self.buffer = self.buffer[position + len(closing_tag):]
                    self.inside_think = False
                    continue

                keep_length = len(closing_tag) - 1
                self.buffer = self.buffer[-keep_length:]
                break

            else:
                opening_tag = "<think>"
                position = self.buffer.find(opening_tag)

                if position != -1:
                    output += self.buffer[:position]
                    self.buffer = self.buffer[position + len(opening_tag):]
                    self.inside_think = True
                    continue

                keep_length = len(opening_tag) - 1

                if len(self.buffer) > keep_length:
                    output += self.buffer[:-keep_length]
                    self.buffer = self.buffer[-keep_length:]

                break

        return output

    def flush(self) -> str:

        if self.inside_think:
            self.buffer = ""
            return ""

        remaining = self.buffer
        self.buffer = ""
        return remaining


async def stream_message(message: str, conversation_id: int | None = None):

    conversation_id, user_message_id, messages = prepare_conversation(
        message,
        conversation_id
    )

    yield {
        "type": "metadata",
        "conversation_id": conversation_id
    }

    logger.info("Sending streaming request to model: %s", LLM_MODEL)

    reply_parts = []
    think_filter = ThinkTagFilter()

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{LLM_BASE_URL}/chat/completions",
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "temperature": LLM_TEMPERATURE,
                    "max_tokens": LLM_MAX_TOKENS,
                    "stream": True
                }
            ) as response:

                response.raise_for_status()

                async for line in response.aiter_lines():

                    if not line.startswith("data: "):
                        continue

                    data = line[6:]

                    if data == "[DONE]":
                        break

                    chunk = json.loads(data)

                    content = chunk["choices"][0]["delta"].get("content")

                    if content:
                        cleaned_content = think_filter.feed(content)

                        if cleaned_content:
                            reply_parts.append(cleaned_content)
                            yield {
                                "type": "token",
                                "content": cleaned_content
                            }

        # Release any remaining text held by the filter.
        remaining_content = think_filter.flush()

        if remaining_content:
            reply_parts.append(remaining_content)
            yield {
                "type": "token",
                "content": remaining_content
            }

    except httpx.ConnectError as exc:
        logger.warning("Local model connection failed: %s", exc)
        update_message_status(user_message_id, "failed", "503", str(exc))
        raise

    except httpx.TimeoutException as exc:
        logger.warning("Local model request timed out: %s", exc)
        update_message_status(user_message_id, "failed", "504", str(exc))
        raise

    except httpx.HTTPStatusError as exc:
        logger.error("Local model returned HTTP %s: %s", exc.response.status_code, exc)
        update_message_status(user_message_id, "failed", "502", str(exc))
        raise

    except httpx.RequestError as exc:
        logger.error("Local model request failed: %s", exc)
        update_message_status(user_message_id, "failed", "502", str(exc))
        raise

    # Persist the complete response once generation has finished.
    reply = "".join(reply_parts).strip()

    save_message(conversation_id, "assistant", reply)

    logger.info("Streaming response completed for conversation %s", conversation_id)


def prepare_conversation(message: str, conversation_id: int | None = None):
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

    return conversation_id, user_message_id, messages