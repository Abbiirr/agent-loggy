from pydantic import BaseModel
from typing import Optional

from app.schemas.CachePolicy import CachePolicyModel


class ChatRequest(BaseModel):
    prompt: str
    project: str
    env: str
    domain: str
    cache: Optional[CachePolicyModel] = None
