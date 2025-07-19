from pydantic import BaseModel


class ChatResponse(BaseModel):
    streamUrl: str