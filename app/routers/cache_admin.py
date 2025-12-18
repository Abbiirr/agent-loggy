# app/routers/cache_admin.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.llm_gateway.gateway import get_llm_cache_gateway


router = APIRouter(prefix="/cache", tags=["cache"])


class CacheDeleteRequest(BaseModel):
    key: str


@router.get("/ping")
def cache_ping():
    gw = get_llm_cache_gateway()
    return {"l1": {"ok": True}, "l2": gw.ping_l2()}


@router.get("/stats")
def cache_stats():
    gw = get_llm_cache_gateway()
    return gw.stats()


@router.post("/delete")
def cache_delete(req: CacheDeleteRequest):
    gw = get_llm_cache_gateway()
    return gw.delete(req.key)


@router.post("/clear-l1")
def cache_clear_l1():
    gw = get_llm_cache_gateway()
    gw.clear_l1()
    return {"ok": True}

