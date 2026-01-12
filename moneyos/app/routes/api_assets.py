from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core import content_autopilot

router = APIRouter(prefix="/api/assets")


class GenerateAssetRequest(BaseModel):
    platform: str = "medium"
    topic: str
    tone: str = "friendly"
    length: str = "medium"
    audience: str = "UK"
    draft_only: bool = True


@router.post("/generate", response_class=JSONResponse)
def generate_asset(request: GenerateAssetRequest):
    payload = content_autopilot.generate_custom_asset(
        topic=request.topic,
        tone=request.tone,
        length=request.length,
        audience=request.audience,
        platform=request.platform,
        draft_only=request.draft_only,
    )
    asset = content_autopilot.create_asset_from_payload(payload)
    return {
        "id": asset.get("uuid") or asset.get("id"),
        "type": asset.get("type"),
        "title": asset.get("title"),
        "status": asset.get("status"),
        "content": asset.get("content_md"),
        "created_at": asset.get("created_at"),
    }
