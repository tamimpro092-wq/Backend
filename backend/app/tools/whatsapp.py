from __future__ import annotations

import logging
from typing import Any, Dict

import httpx
from ..settings import settings

logger = logging.getLogger("tools.whatsapp")


def send_reply(to: str, text: str) -> Dict[str, Any]:
    if bool(settings.DRY_RUN) or not (settings.WHATSAPP_PHONE_NUMBER_ID and settings.WHATSAPP_ACCESS_TOKEN):
        return {"ok": True, "simulated": True, "to": to, "text": text}

    try:
        url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}

        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                return {"ok": False, "error": "whatsapp_error", "status_code": r.status_code, "body": r.text}
            return {"ok": True, "simulated": False, "result": r.json()}
    except Exception as e:
        logger.exception("whatsapp_exception", extra={"extra": {"err": str(e)}})
        return {"ok": False, "error": "exception", "message": str(e)}
