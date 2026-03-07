"""
Outbound Campaign API Routes
"""
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# In-memory campaign store (replace with DB in production)
_campaigns: dict = {}


class CampaignRequest(BaseModel):
    name: str
    type: str           # "reminder" | "followup" | "vaccination"
    patient_ids: List[str]
    message_template: str
    scheduled_at: str   # ISO datetime


@router.post("/create")
async def create_campaign(req: CampaignRequest):
    import uuid
    campaign_id = str(uuid.uuid4())
    _campaigns[campaign_id] = {
        "id": campaign_id,
        "name": req.name,
        "type": req.type,
        "patient_ids": req.patient_ids,
        "message_template": req.message_template,
        "scheduled_at": req.scheduled_at,
        "status": "scheduled",
    }
    return {"success": True, "campaign_id": campaign_id}


@router.get("/list")
async def list_campaigns():
    return {"campaigns": list(_campaigns.values())}


@router.post("/trigger/{campaign_id}")
async def trigger_campaign(campaign_id: str):
    if campaign_id not in _campaigns:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign not found")
    _campaigns[campaign_id]["status"] = "running"
    # In a real system, this would enqueue outbound calls
    return {"success": True, "message": f"Campaign {campaign_id} triggered"}
