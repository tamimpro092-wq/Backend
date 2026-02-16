from __future__ import annotations

import logging
from typing import Dict

import httpx
from sqlmodel import Session

from ..db import engine
from ..models import ProductDraft
from ..settings import settings

logger = logging.getLogger("tools.shopify")


def draft_product(source: str = "research") -> Dict:
    title = "Winning Product"
    description = "High potential product draft."
    cost = 12.0

    if source == "research":
        title = "AirBrush Pro Mini Compressor"
        description = "Compact airbrush kit for crafts and nail art with adjustable pressure."
        cost = 24.0

    with Session(engine) as session:
        draft = ProductDraft(
            title=title,
            description=description,
            price=0.0,
            currency="USD",
            status="draft",
            meta={"cost": cost, "source": source},
        )
        session.add(draft)
        session.commit()
        session.refresh(draft)

    return {"ok": True, "draft_id": draft.id, "title": draft.title, "status": draft.status, "dry_run": bool(settings.DRY_RUN)}


def _shopify_headers() -> Dict[str, str]:
    return {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def publish_product(product_id: int) -> Dict:
    with Session(engine) as session:
        draft = session.get(ProductDraft, product_id)

        if not draft:
            return {"ok": True, "simulated": True, "product_id": product_id, "note": "Draft not found; simulated publish."}

        if bool(settings.DRY_RUN) or not (settings.SHOPIFY_SHOP and settings.SHOPIFY_ACCESS_TOKEN):
            draft.status = "simulated_published"
            session.add(draft)
            session.commit()
            return {
                "ok": True,
                "simulated": True,
                "draft_id": draft.id,
                "status": draft.status,
                "note": "DRY_RUN or missing creds: no external call made.",
            }

        # Real mode: set product status active (best-effort)
        ext_id = draft.external_id or str(draft.id)
        url = f"https://{settings.SHOPIFY_SHOP}/admin/api/{settings.SHOPIFY_API_VERSION}/products/{ext_id}.json"
        payload = {"product": {"id": int(ext_id), "status": "active"}}

        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.put(url, headers=_shopify_headers(), json=payload)
                if r.status_code >= 400:
                    logger.warning("shopify_publish_failed", extra={"extra": {"status": r.status_code, "body": r.text}})
                    return {"ok": False, "error": "shopify_error", "status_code": r.status_code, "body": r.text}

            draft.status = "published"
            session.add(draft)
            session.commit()
            return {"ok": True, "simulated": False, "draft_id": draft.id, "status": draft.status}
        except Exception as e:
            logger.exception("shopify_publish_exception", extra={"extra": {"err": str(e)}})
            return {"ok": False, "error": "exception", "message": str(e)}
