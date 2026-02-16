from __future__ import annotations

from typing import Any, Dict


def missed_call_followup(phone: str = "", reason: str = "missed_call") -> Dict[str, Any]:
    msg = (
        "Hi! We tried to reach you but missed you. "
        "Reply here with your order number and how we can help, and our team will follow up."
    )
    return {"ok": True, "phone": phone, "reason": reason, "message": msg}
