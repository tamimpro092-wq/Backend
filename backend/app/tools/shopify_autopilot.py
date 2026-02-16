from __future__ import annotations

import math
import re
from typing import Any, Dict, List

import httpx
from sqlmodel import Session

from ..db import engine
from ..models import ProductDraft
from ..settings import settings
from .research_multisource import find_winning_product_multisource
from .stock_images import pexels_search_image


def _headers() -> Dict[str, str]:
    return {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _round_psych(x: float) -> float:
    return math.floor(x) + 0.99


def _price(cost: float) -> Dict[str, float]:
    factor = 3.0 if cost < 10 else 2.6
    p = _round_psych(cost * factor)
    c = _round_psych(p * 1.25)
    return {"price": float(p), "compare_at": float(c)}


def _keywords(title: str, niche: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", title.lower())
    words = [w for w in words if len(w) > 2]
    niche_words = re.findall(r"[a-z0-9]+", (niche or "general").lower())
    niche_words = [w for w in niche_words if len(w) > 2]
    out = []
    for w in words + niche_words:
        if w not in out:
            out.append(w)
    return out[:15]


def _tags(keys: List[str]) -> str:
    return ", ".join(keys[:15])


def _big_seo_html(title: str, niche: str, short_desc: str, keys: List[str]) -> str:
    kline = ", ".join(keys[:10])
    benefits = [
        "Designed for daily use and consistent results",
        "Simple setup — works great right out of the box",
        "High-perceived value that converts well",
        "Giftable and easy to ship",
        "Strong niche fit with broad demand",
    ]
    bullets = "".join([f"<li>{b}</li>" for b in benefits])

    specs = [
        ("Category", niche.title()),
        ("Style", "Modern"),
        ("Use case", "Everyday"),
        ("Shipping", "Lightweight / easy to package"),
        ("Support", "Standard store support"),
    ]
    specs_html = "".join([f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>" for k, v in specs])

    faq = [
        ("Is it easy to use?", "Yes — it’s designed for simple daily use."),
        ("Is it giftable?", "Absolutely. It’s a practical item people love to receive."),
        ("How fast can it ship?", "Fast shipping depends on your fulfillment setup, but it’s lightweight and easy to handle."),
        ("Does it work for this niche?", f"Yes — it’s a strong match for {niche}."),
    ]
    faq_html = "".join([f"<details><summary><strong>{q}</strong></summary><p>{a}</p></details>" for q, a in faq])

    return f"""
<h1>{title}</h1>
<p><strong>Best for:</strong> {niche.title()} shoppers • <strong>Keywords:</strong> {kline}</p>

<p>{short_desc}</p>

<h2>Why this product sells</h2>
<ul>
{bullets}
</ul>

<h2>What you get</h2>
<ul>
<li>1× {title}</li>
<li>Simple instructions included</li>
<li>Quality checked packaging</li>
</ul>

<h2>Specifications</h2>
<table>
{specs_html}
</table>

<h2>FAQ</h2>
{faq_html}

<p><em>SEO Notes:</em> This description is optimized for buyer intent keywords, readable structure, and conversion-focused sections.</p>
""".strip()


def add_product_full_auto(niche: str | None = None, inventory_qty: int | None = None) -> Dict[str, Any]:
    niche_final = (niche or getattr(settings, "STORE_NICHE", "general") or "general").strip()
    qty = int(inventory_qty or getattr(settings, "DEFAULT_INVENTORY_QTY", 100) or 100)

    # 1) research (now should never fail due to your catalog-based research_multisource)
    r = find_winning_product_multisource(niche=niche_final)
    if not r.get("ok"):
        return {"ok": False, "error": "live_research_failed", "details": r}

    top = r["top_pick"]
    title = top["title"]
    short_desc = top["description"]
    cost = float(top.get("suggested_cost") or 10.0)

    # 2) pricing
    pr = _price(cost)
    price = pr["price"]
    compare_at = pr["compare_at"]

    # 3) seo
    keys = _keywords(title, niche_final)
    tags = _tags(keys)
    body_html = _big_seo_html(title, niche_final, short_desc, keys)

    # 4) image
    img = pexels_search_image(f"{title} product photo", orientation="square")
    image_url = img.get("image_url") if img.get("ok") else None

    # 5) DRY_RUN or missing shopify
    if bool(settings.DRY_RUN) or not (settings.SHOPIFY_SHOP and settings.SHOPIFY_ACCESS_TOKEN):
        with Session(engine) as session:
            draft = ProductDraft(
                title=title,
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
                    "keywords": keys,
                    "image_url": image_url,
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
            "title": title,
            "price": price,
            "compare_at": compare_at,
            "image_url": image_url,
            "chosen_niche": niche_final,
            "note": "DRY_RUN or missing Shopify creds: product not created in Shopify.",
        }

    # 6) create product in shopify
    create_url = f"https://{settings.SHOPIFY_SHOP}/admin/api/{settings.SHOPIFY_API_VERSION}/products.json"

    payload: Dict[str, Any] = {
        "product": {
            "title": title,
            "body_html": body_html,
            "vendor": settings.BRAND_NAME,
            "product_type": niche_final,
            "tags": tags,
            "status": "active",
            "variants": [
                {
                    "price": f"{price:.2f}",
                    "compare_at_price": f"{compare_at:.2f}",
                    "sku": re.sub(r"[^A-Za-z0-9]+", "-", title.upper()).strip("-")[:32],
                    "inventory_management": "shopify",
                    "inventory_policy": "continue",
                    "inventory_quantity": int(qty),
                    "requires_shipping": True,
                }
            ],
        }
    }

    if image_url:
        payload["product"]["images"] = [{"src": image_url, "alt": title}]

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(create_url, headers=_headers(), json=payload)
            if resp.status_code >= 400:
                return {"ok": False, "error": "shopify_http_error", "status_code": resp.status_code, "body": resp.text}

            data = resp.json() or {}
            prod = data.get("product") or {}
            pid = prod.get("id")
            handle = prod.get("handle")

        with Session(engine) as session:
            draft = ProductDraft(
                title=title,
                description=body_html,
                price=price,
                currency="USD",
                status="published",
                external_id=str(pid) if pid else None,
                meta={
                    "niche": niche_final,
                    "cost": cost,
                    "compare_at": compare_at,
                    "tags": tags,
                    "keywords": keys,
                    "image_url": image_url,
                    "research": r,
                    "shopify_handle": handle,
                },
            )
            session.add(draft)
            session.commit()
            session.refresh(draft)

        admin_url = f"https://{settings.SHOPIFY_SHOP}/admin/products/{pid}" if pid else None

        return {
            "ok": True,
            "simulated": False,
            "draft_id": draft.id,
            "shopify_product_id": pid,
            "shopify_handle": handle,
            "admin_url": admin_url,
            "title": title,
            "price": price,
            "compare_at": compare_at,
            "image_url": image_url,
            "chosen_niche": niche_final,
        }

    except Exception as e:
        return {"ok": False, "error": "exception", "tool": "shopify.autopilot_add_product", "message": str(e)}
