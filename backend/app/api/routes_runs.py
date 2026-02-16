from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..deps import get_session
from ..agent.orchestrator import Orchestrator

router = APIRouter(prefix="/api", tags=["runs"])


@router.post("/run/shopify")
def run_shopify(session: Session = Depends(get_session), payload: dict | None = None):
    action = (payload or {}).get("action", "draft_product")
    orch = Orchestrator(session=session)
    text_map = {
        "draft_product": "Add a winning product and prepare it to sell",
        "analyze_pricing": "Analyze product and propose best price",
        "publish": f"Publish product {(payload or {}).get('product_id', '123')}",
    }
    return orch.handle_command(text_map.get(action, "Add a winning product and prepare it to sell"))


@router.post("/run/inbox")
def run_inbox(session: Session = Depends(get_session), payload: dict | None = None):
    action = (payload or {}).get("action", "triage")
    orch = Orchestrator(session=session)
    if action == "triage":
        return orch.handle_command("Triage inbox")
    return orch.handle_command("Show me system status")
