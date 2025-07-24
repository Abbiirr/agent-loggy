from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    project: str
    env: str
    domain: str