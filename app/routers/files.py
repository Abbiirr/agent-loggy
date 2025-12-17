# app/routers/files.py
"""
File download API routes.
"""

import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import settings


router = APIRouter(tags=["files"])


@router.get("/download/")
def download_file(filename: str = Query(..., description="Name of the file to download")):
    """
    Download an analysis file by filename.
    """
    analysis_dir = settings.ANALYSIS_DIR

    # Prevent directory traversal
    safe_path = os.path.normpath(os.path.join(analysis_dir, filename))
    if not safe_path.startswith(os.path.normpath(analysis_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=safe_path,
        filename=filename,
        media_type="application/octet-stream",
    )
