import json
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.chat_service import stream_message
from app.db.database import get_conversation, get_messages, get_all_conversations

router = APIRouter(
    tags=["Chat"]
)


@router.post("/chat")
async def chat(request: ChatRequest):

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    if request.conversation_id is not None:
        conversation = get_conversation(request.conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

    async def event_stream():

        try:
            async for event in stream_message(
                request.message,
                request.conversation_id
            ):
                event_type = event["type"]

                yield (
                    f"event: {event_type}\n"
                    f"data: {json.dumps(event)}\n\n"
                )

        except httpx.ConnectError:
            error = {
                "message": "The local language model is unavailable. Check whether vLLM is running."
            }
            yield f"event: error\ndata: {json.dumps(error)}\n\n"

        except httpx.TimeoutException:
            error = {
                "message": "The model took too long to respond. Please try again."
            }
            yield f"event: error\ndata: {json.dumps(error)}\n\n"

        except httpx.HTTPStatusError:
            error = {
                "message": "The local model returned an unsuccessful response."
            }
            yield f"event: error\ndata: {json.dumps(error)}\n\n"

        except httpx.RequestError:
            error = {
                "message": "Could not communicate with the local language model."
            }
            yield f"event: error\ndata: {json.dumps(error)}\n\n"

        else:
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/chat/{conversation_id}/messages")
async def get_chat_messages(conversation_id: int):

    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    messages = get_messages(conversation_id)

    return {
        "conversation_id": conversation_id,
        "messages": messages
    }

@router.get("/conversations")
async def list_conversations():
    conversations = get_all_conversations()

    return {
        "conversations": conversations
    }