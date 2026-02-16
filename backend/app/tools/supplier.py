from __future__ import annotations

from typing import Any, Dict


def outreach_draft(product_name: str = "Product", quantity: int = 200) -> Dict[str, Any]:
    msg = (
        f"Hello! We’re interested in sourcing {product_name}.\n"
        f"Please share MOQ, unit price for {quantity} units, lead time, and shipping options.\n"
        "Also confirm packaging details and whether you can provide samples.\n"
    )
    return {"ok": True, "product_name": product_name, "quantity": quantity, "draft_email": msg}
