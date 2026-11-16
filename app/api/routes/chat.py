from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import process_message
from app.db.database import get_conversation, get_messages, get_all_conversations

router = APIRouter(
    tags=["Chat"]
)

@router.post("/chat", response_model=ChatResponse)
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

    conversation_id, reply = await process_message(
        request.message,
        request.conversation_id
    )

    return {
        "received_message": reply,
        "conversation_id": conversation_id
    }

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