from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(max_length=10000)
    conversation_id: int | None = None

class ChatResponse(BaseModel):
    received_message: str
    conversation_id: int