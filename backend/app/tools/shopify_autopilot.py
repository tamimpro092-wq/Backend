from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Tuple

import httpx
from sqlmodel import Session

from ..db import engine
from ..models import ProductDraft
from ..settings import settings
from .stock_images import pexels_search_image
from .research_multisource import (
    find_winning_product_multisource,
    find_winning_product_multisource_for_many,
)


def _shopify_headers() -> Dict[str, str]:
    return {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _round_psych(x: float) -> float:
    return math.floor(x) + 0.99


def _make_price(cost: float) -> Tuple[float, float]:
    factor = 3.0 if cost < 10 else 2.6
    price = _round_psych(cost * factor)
    compare_at = _round_psych(price * 1.25)
    return float(price), float(compare_at)


def _keywords_from_title(title: str, niche: str) -> List[str]:
    words = re.findall(r"[A-Za-z0-9]+", title.lower())
    words = [w for w in words if len(w) > 2]
    base = list(dict.fromkeys(words))[:8]
    niche_words = re.findall(r"[A-Za-z0-9]+", (niche or "general").lower())
    niche_words = [w for w in niche_words if len(w) > 2]
    for w in niche_words[:4]:
        if w not in base:
            base.append(w)
    return base[:12]


def _seo_title(title: str) -> str:
    t = title.strip()
    if len(t) > 70:
        t = t[:67].rstrip() + "..."
    return t


def _seo_html_description(title: str, short_desc: str, bullets: List[str], keywords: List[str]) -> str:
    kw = ", ".join(keywords[:8])
    bullets_html = "".join([f"<li>{b}</li>" for b in bullets])
    return f"""
<h2>{title}</h2>
<p>{short_desc}</p>

<h3>Why you’ll love it</h3>
<ul>
{bullets_html}
</ul>

<h3>Perfect for</h3>
<ul>
<li>Daily use</li>
<li>Gifting</li>
<li>Home, office, or travel</li>
</ul>

<p><strong>Keywords:</strong> {kw}</p>
""".strip()


def _tags_from_keywords(keywords: List[str]) -> str:
    tags = []
    for k in keywords:
        k2 = k.strip().lower()
        if k2 and k2 not in tags:
            tags.append(k2)
    return ", ".join(tags[:15])


def _first_location_id(client: httpx.Client) -> int | None:
    url = f"https://{settings.SHOPIFY_SHOP}/admin/api/{settings.SHOPIFY_API_VERSION}/locations.json"
    r = client.get(url, headers=_shopify_headers())
    if r.status_code >= 400:
        return None
    data = r.json() or {}
    locs = data.get("locations") or []
    # pick first active location
    for loc in locs:
        if loc.get("active") is True and loc.get("id"):
            return int(loc["id"])
    # fallback: first with id
    for loc in locs:
        if loc.get("id"):
            return int(loc["id"])
    return None


def _set_inventory_level(client: httpx.Client, inventory_item_id: int, location_id: int, qty: int) -> Dict[str, Any]:
    url = f"https://{settings.SHOPIFY_SHOP}/admin/api/{settings.SHOPIFY_API_VERSION}/inventory_levels/set.json"
    payload = {"location_id": location_id, "inventory_item_id": inventory_item_id, "available": int(qty)}
    r = client.post(url, headers=_shopify_headers(), json=payload)
    if r.status_code >= 400:
        return {"ok": False, "status_code": r.status_code, "body": r.text}
    return {"ok": True, "result": r.json()}


def add_product_full_auto(
    niche: str | None = None,
    inventory_qty: int | None = None,
) -> Dict[str, Any]:
    raw_niche = (niche or settings.STORE_NICHE or "general").strip()
    niche_list = [x.strip() for x in raw_niche.split(",") if x.strip()]
    qty = int(inventory_qty or getattr(settings, "DEFAULT_INVENTORY_QTY", 100) or 100)

    # 1) Multi-source research
    if len(niche_list) <= 1:
        niche_final = niche_list[0] if niche_list else "general"
        r = find_winning_product_multisource(niche=niche_final)
    else:
        r = find_winning_product_multisource_for_many(niches=niche_list)
        niche_final = r.get("chosen_niche") or (niche_list[0] if niche_list else "general")

    if not r.get("ok"):
        return {"ok": False, "error": "live_research_failed", "details": r}

    top = r["top_pick"]
    title_raw = top["title"]
    short_desc = top["description"]
    cost = float(top.get("suggested_cost") or 10.0)

    # 2) Pricing
    price, compare_at = _make_price(cost)

    # 3) SEO copy
    seo_title = _seo_title(title_raw)
    keywords = _keywords_from_title(seo_title, niche_final)
    bullets = [
        "Easy to use and set up in minutes",
        "Built for consistent results every time",
        "Great value—designed for everyday use",
        "A smart gift that people actually keep using",
    ]
    body_html = _seo_html_description(seo_title, short_desc, bullets, keywords)
    tags = _tags_from_keywords(keywords)

    # 4) Image
    img_query = f"{seo_title} product photo"
    img = pexels_search_image(img_query, orientation="square")
    image_url = img.get("image_url") if img.get("ok") else None

    # 5) DRY_RUN / missing creds
    if bool(settings.DRY_RUN) or not (settings.SHOPIFY_SHOP and settings.SHOPIFY_ACCESS_TOKEN):
        with Session(engine) as session:
            draft = ProductDraft(
                title=seo_title,
                description=body_html,
                price=price,
                currency="USD",
                status="simulated_published",
                external_id=None,
                meta={
                    "niche": niche_final,
                    "cost": cost,
                    "compare_at": compare_at,
                    "tags": tags,
                    "keywords": keywords,
                    "image_url": image_url,
                    "image_provider": img.get("provider"),
                    "research": r,
                },
            )
            session.add(draft)
            session.commit()
            session.refresh(draft)

        return {
            "ok": True,
            "simulated": True,
            "draft_id": draft.id,
            "title": seo_title,
            "price": price,
            "compare_at": compare_at,
            "image_url": image_url,
            "chosen_niche": niche_final,
            "note": "DRY_RUN or missing Shopify creds: product not created in Shopify.",
        }

    # 6) Create product (WITHOUT inventory_quantity)
    create_url = f"https://{settings.SHOPIFY_SHOP}/admin/api/{settings.SHOPIFY_API_VERSION}/products.json"

    product_payload: Dict[str, Any] = {
        "product": {
            "title": seo_title,
            "body_html": body_html,
            "vendor": settings.BRAND_NAME,
            "product_type": niche_final,
            "tags": tags,
            "status": "active",
            "variants": [
                {
                    "price": f"{price:.2f}",
                    "compare_at_price": f"{compare_at:.2f}",
                    "sku": re.sub(r"[^A-Za-z0-9]+", "-", seo_title.upper()).strip("-")[:32],
                    "inventory_management": "shopify",
                    "inventory_policy": "continue",
                    "requires_shipping": True,
                }
            ],
        }
    }

    if image_url:
        product_payload["product"]["images"] = [{"src": image_url, "alt": seo_title}]

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(create_url, headers=_shopify_headers(), json=product_payload)
            if resp.status_code >= 400:
                return {"ok": False, "error": "shopify_http_error", "status_code": resp.status_code, "body": resp.text}

            data = resp.json() or {}
            prod = (data.get("product") or {})
            shopify_id = prod.get("id")
            handle = prod.get("handle")

            # ✅ Set inventory correctly via inventory_levels/set
            inv_note = None
            variant0 = (prod.get("variants") or [{}])[0] or {}
            inventory_item_id = variant0.get("inventory_item_id")
            location_id = _first_location_id(client)

            if inventory_item_id and location_id:
                inv_res = _set_inventory_level(client, int(inventory_item_id), int(location_id), int(qty))
                if not inv_res.get("ok"):
                    inv_note = {"inventory_set_failed": inv_res}
            else:
                inv_note = {"inventory_set_skipped": {"inventory_item_id": inventory_item_id, "location_id": location_id}}

        # Save to DB
        with Session(engine) as session:
            draft = ProductDraft(
                title=seo_title,
                description=body_html,
                price=price,
                currency="USD",
                status="published",
                external_id=str(shopify_id) if shopify_id else None,
                meta={
                    "niche": niche_final,
                    "cost": cost,
                    "compare_at": compare_at,
                    "tags": tags,
                    "keywords": keywords,
                    "image_url": image_url,
                    "image_provider": img.get("provider") if img.get("ok") else None,
                    "pexels_url": img.get("pexels_url"),
                    "research": r,
                    "shopify_handle": handle,
                    "inventory": inv_note,
                },
            )
            session.add(draft)
            session.commit()
            session.refresh(draft)

        admin_url = f"https://{settings.SHOPIFY_SHOP}/admin/products/{shopify_id}" if shopify_id else None

        return {
            "ok": True,
            "simulated": False,
            "draft_id": draft.id,
            "shopify_product_id": shopify_id,
            "shopify_handle": handle,
            "admin_url": admin_url,
            "title": seo_title,
            "price": price,
            "compare_at": compare_at,
            "image_url": image_url,
            "chosen_niche": niche_final,
            "confirmed_multisource": bool((r.get("top_pick") or {}).get("confirmed")),
        }

    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}
