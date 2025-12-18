from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CachePolicyModel(BaseModel):
    enabled: bool = True
    no_cache: bool = False
    no_store: bool = False
    ttl_seconds: Optional[int] = Field(default=None, ge=1)
    s_maxage_seconds: Optional[int] = Field(default=None, ge=1)
    namespace: Optional[str] = None

