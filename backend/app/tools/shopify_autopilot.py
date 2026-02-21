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


def _make_price_bd(cost_bd: float) -> Tuple[float, float]:
    # BD-style pricing feel (still uses store currency, but matches your BD example)
    factor = 2.2 if cost_bd >= 800 else 2.8
    price = _round_psych(cost_bd * factor)
    compare_at = _round_psych(price * 1.20)
    return float(price), float(compare_at)


def _slugify(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        s = "product"
    return s[:60].rstrip("-")


def _clean_product_type(niche: str) -> str:
    """
    Normalizes niche-like text. Not final safety.
    """
    s = (niche or "general").strip().lower()
    s = re.sub(r"\b(in my store|in store|my store|shopify|store|shop)\b", "", s, flags=re.I)
    s = re.sub(r"[^a-z0-9 &\-\_]+", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        s = "general"
    return s[:80].rstrip()


def _safe_product_type(value: str | None) -> str:
    """
    ✅ FINAL GUARANTEE:
    Shopify product_type/custom_product_type max 255.
    We enforce a strong small limit so it can NEVER fail.
    """
    s = (value or "general").strip().lower()

    # Remove common command noise
    s = re.sub(r"\b(in my store|in store|my store|shopify|store|shop)\b", "", s, flags=re.I)
    s = re.sub(r"[^a-z0-9 &\-\_]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    if not s:
        s = "general"

    # ✅ Keep very short & category-like (safe for Shopify + clean UI)
    if len(s) > 50:
        s = s[:50].rstrip()

    return s


def _seo_title_bd(base_title: str, niche: str) -> str:
    """
    60–70 chars target: keyword + benefit + COD BD
    """
    base = (base_title or "Product").strip()
    niche_clean = _safe_product_type(niche).title()

    t = f"{base} – Best Price | Cash on Delivery BD"
    if len(t) > 70:
        t = t[:70].rstrip()
        t = re.sub(r"[\-|–|\|]\s*$", "", t).strip()

    if len(t) < 45:
        t = f"{base} – {niche_clean} | COD BD"
        if len(t) > 70:
            t = t[:70].rstrip()

    return t


def _keywords(title: str, niche: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", (title or "").lower())
    words = [w for w in words if len(w) > 2]
    niche_words = re.findall(r"[a-z0-9]+", (niche or "general").lower())
    niche_words = [w for w in niche_words if len(w) > 2]
    out: List[str] = []
    for w in words + niche_words:
        if w not in out:
            out.append(w)
    return out[:15]


def _tags_from_keywords(keys: List[str]) -> str:
    return ", ".join(keys[:15])


def _is_sofa_cover(title: str, niche: str) -> bool:
    s = f"{title} {niche}".lower()
    return ("sofa" in s and "cover" in s) or ("sofa cover" in s)


def _variants(title: str, niche: str, price: float, compare_at: float, qty: int) -> List[Dict[str, Any]]:
    """
    Safe variant logic:
    - Sofa cover => Size + Color variants (high conversion)
    - Otherwise => single variant (stable)
    """
    sku_base = re.sub(r"[^A-Za-z0-9]+", "-", (title or "SKU").upper()).strip("-")[:18]

    if _is_sofa_cover(title, niche):
        sizes = ["1 Seater", "2 Seater", "3 Seater", "L Shape"]
        colors = ["Beige", "Grey"]  # keep simple and stable

        pairs = [(sz, col) for sz in sizes for col in colors]  # 8 variants
        per_qty = max(5, int(qty / max(1, len(pairs))))

        variants = []
        for i, (sz, col) in enumerate(pairs):
            variants.append(
                {
                    "option1": sz,
                    "option2": col,
                    "price": f"{price:.2f}",
                    "compare_at_price": f"{compare_at:.2f}",
                    "sku": f"{sku_base}-S{i+1}",
                    "inventory_management": "shopify",
                    "inventory_policy": "continue",
                    "inventory_quantity": int(per_qty),
                    "requires_shipping": True,
                }
            )
        return variants

    return [
        {
            "price": f"{price:.2f}",
            "compare_at_price": f"{compare_at:.2f}",
            "sku": f"{sku_base}-01",
            "inventory_management": "shopify",
            "inventory_policy": "continue",
            "inventory_quantity": int(qty),
            "requires_shipping": True,
        }
    ]


def _seo_description_bd(
    title: str,
    niche: str,
    short_desc: str,
    keys: List[str],
    market_signals: List[str],
) -> str:
    features = [
        "Premium quality material",
        "Washable & durable",
        "Easy fitting / easy use",
        "Perfect for daily use",
        "Cash on Delivery available",
    ]
    feats_html = "".join([f"<li>{x}</li>" for x in features])

    who_for = [
        f"Perfect for {niche.title()} customers",
        "Great for gifting",
        "Suitable for home & office use",
    ]
    who_html = "".join([f"<li>{x}</li>" for x in who_for])

    signals_html = "".join([f"<li>{x}</li>" for x in (market_signals or [])])

    kw_line = ", ".join(keys[:10])
    handle = _slugify(title)

    faq = [
        ("Is it washable?", "Yes, it’s easy to wash and made for daily use."),
        ("Is Cash on Delivery available?", "Yes, Cash on Delivery is available across Bangladesh."),
        ("How do I order?", "Place your order from the website. WhatsApp option can also be added."),
        ("Delivery time?", "Usually 1–3 days depending on location."),
    ]
    faq_html = "".join([f"<details><summary><strong>{q}</strong></summary><p>{a}</p></details>" for q, a in faq])

    trust = [
        "✔ Cash on Delivery (BD)",
        "✔ Easy Return Policy",
        "✔ Custom Support via WhatsApp",
        "✔ Quality Check Before Delivery",
    ]
    trust_html = "<br/>".join(trust)

    return f"""
<h2>{title}</h2>

<p><strong>Hook:</strong> {short_desc} Upgrade your home in minutes!</p>

<h3>✅ Features</h3>
<ul>{feats_html}</ul>

<h3>✅ Who it’s for</h3>
<ul>{who_html}</ul>

<h3>✅ Market analysis (autopilot)</h3>
<ul>
<li>High buyer intent in <strong>{niche.title()}</strong> niche</li>
<li>Search keywords: <strong>{kw_line}</strong></li>
{signals_html}
</ul>

<h3>✅ Delivery & Payment</h3>
<ul>
<li>Delivery all over Bangladesh</li>
<li><strong>Cash on Delivery</strong> available</li>
</ul>

<h3>✅ Trust Boost</h3>
<p>{trust_html}</p>

<h3>✅ FAQ</h3>
{faq_html}

<h3>SEO</h3>
<p><strong>Meta Title:</strong> {title}</p>
<p><strong>Meta Description:</strong> Buy {niche.title()} product in Bangladesh with Cash on Delivery. Premium quality, fast delivery, order now!</p>
<p><strong>URL Handle:</strong> /{handle}</p>
""".strip()


# ============================
# ✅ IMAGE LOGIC (ONLY CHANGE)
# ============================

def _strip_seo_tail_for_images(title: str) -> str:
    """
    Remove marketing/SEO tails so image search focuses on the real product name.
    """
    s = (title or "").strip()

    # Remove BD marketing tail patterns
    s = re.sub(r"\s*[–\-]\s*best price\s*\|\s*cash on delivery bd\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*\|\s*cash on delivery bd\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*\|\s*cod bd\s*$", "", s, flags=re.I)

    # Remove any tail that contains delivery/cod/bangladesh keywords
    s = re.sub(r"\s*[–\-]\s*.*\b(cod|delivery|bangladesh|bd)\b.*$", "", s, flags=re.I).strip()

    # Final tidy
    s = re.sub(r"\s+", " ", s).strip()
    return s or (title or "product")


def _build_strict_product_query(title: str) -> str:
    """
    Build a STRICT product-only query so Pexels doesn't return random niche content.
    """
    s = _strip_seo_tail_for_images(title).lower()

    # Remove marketing + generic commerce words
    stop = {
        "best", "price", "offer", "sale", "discount", "bd", "bangladesh", "cod",
        "delivery", "cash", "on", "available", "premium", "quality", "buy", "order",
        "online", "store", "shop", "new", "original", "latest"
    }

    tokens = re.findall(r"[a-z0-9]+", s)
    tokens = [t for t in tokens if t not in stop and len(t) > 1]

    if not tokens:
        return "product"

    # Keep last few tokens (usually most product-specific)
    if len(tokens) > 6:
        tokens = tokens[-6:]

    return " ".join(tokens).strip() or "product"


def _image_urls(title: str, niche: str) -> List[str]:
    """
    ✅ Your requirement:
    - Image search must follow the REAL PRODUCT, not the niche ("summer").
    - So we search ONLY using product title keywords.
    """
    core = _build_strict_product_query(title)

    # Strict product-based queries (no niche usage)
    queries = [
        f"{core} product photo",
        f"{core} white background product",
        f"{core} close up product",
        f"{core} in hand product",
        f"{core} lifestyle product",
        f"{core} packaging product",
        f"{core} isolated product",
    ]

    bad_tokens = {"flower", "portrait", "model", "wedding", "baby", "nature", "cat", "dog", "landscape"}

    urls: List[str] = []
    for q in queries:
        r = pexels_search_image(q, orientation="square")
        if r.get("ok") and r.get("image_url"):
            u = str(r["image_url"])
            test = (q + " " + u).lower()
            if any(bt in test for bt in bad_tokens):
                continue
            if u not in urls:
                urls.append(u)
        if len(urls) >= 7:
            break

    # Ensure at least 1 image if possible
    if not urls:
        r = pexels_search_image(f"{core} product", orientation="square")
        if r.get("ok") and r.get("image_url"):
            urls.append(str(r["image_url"]))
    return urls


def add_product_full_auto(
    niche: str | None = None,
    inventory_qty: int | None = None,
) -> Dict[str, Any]:
    # IMPORTANT: raw niche might accidentally include the whole command text
    raw_niche = (niche or getattr(settings, "STORE_NICHE", "") or "general").strip()
    niche_list = [x.strip() for x in raw_niche.split(",") if x.strip()]
    qty = int(inventory_qty or getattr(settings, "DEFAULT_INVENTORY_QTY", 100) or 100)

    # 1) Research (catalog-based, avoids repeats via research_multisource.py)
    if len(niche_list) <= 1:
        niche_guess = niche_list[0] if niche_list else "general"
        niche_final = _clean_product_type(niche_guess)
        r = find_winning_product_multisource(niche=niche_final)
    else:
        r = find_winning_product_multisource_for_many(niches=niche_list)
        niche_final = _clean_product_type(r.get("chosen_niche") or niche_list[0])

    if not r.get("ok"):
        return {"ok": False, "error": "live_research_failed", "details": r}

    # ✅ FINAL SAFE product_type for Shopify (prevents 422 forever)
    product_type = _safe_product_type(niche_final)

    top = r["top_pick"]
    base_title = top.get("title") or "Product"
    short_desc = top.get("description") or "High-demand product for everyday use."
    cost_bd = float(top.get("suggested_cost") or 500.0)

    # 2) Pricing
    price, compare_at = _make_price_bd(cost_bd)

    # 3) SEO title/keywords/tags/description
    seo_title = _seo_title_bd(base_title, product_type)
    keys = _keywords(seo_title, product_type)
    tags = _tags_from_keywords(keys)
    market_signals = (r.get("market_signals") or []) if isinstance(r, dict) else []
    body_html = _seo_description_bd(seo_title, product_type, short_desc, keys, market_signals)

    # 4) Images (5–7) ✅ IMPORTANT: use base_title so images follow the actual product
    urls = _image_urls(base_title, product_type)
    image_url = urls[0] if urls else None

    # 5) Variants
    variants = _variants(seo_title, product_type, price, compare_at, qty)

    # 6) DRY_RUN / missing creds
    if bool(settings.DRY_RUN) or not (settings.SHOPIFY_SHOP and settings.SHOPIFY_ACCESS_TOKEN):
        with Session(engine) as session:
            draft = ProductDraft(
                title=seo_title,
                description=body_html,
                price=price,
                currency="BDT",
                status="simulated_published",
                external_id="",
                meta={
                    "niche": product_type,
                    "cost": cost_bd,
                    "compare_at": compare_at,
                    "tags": tags,
                    "keywords": keys,
                    "image_urls": urls,
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
            "image_urls": urls,
            "chosen_niche": product_type,
            "note": "DRY_RUN or missing Shopify creds: product not created in Shopify.",
        }

    # 7) Create product in Shopify
    create_url = f"https://{settings.SHOPIFY_SHOP}/admin/api/{settings.SHOPIFY_API_VERSION}/products.json"

    payload: Dict[str, Any] = {
        "product": {
            "title": seo_title,
            "body_html": body_html,
            "vendor": settings.BRAND_NAME,
            "product_type": product_type,  # ✅ SAFE VALUE
            "tags": tags,
            "handle": _slugify(seo_title),
            "status": "active",
            "variants": variants,
        }
    }

    if urls:
        payload["product"]["images"] = [{"src": u, "alt": seo_title} for u in urls]

    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(create_url, headers=_shopify_headers(), json=payload)
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "error": "shopify_http_error",
                    "status_code": resp.status_code,
                    "body": resp.text,
                }

            data = resp.json() or {}
            prod = (data.get("product") or {})
            shopify_id = prod.get("id")
            handle = prod.get("handle")

        with Session(engine) as session:
            draft = ProductDraft(
                title=seo_title,
                description=body_html,
                price=price,
                currency="BDT",
                status="published",
                external_id=str(shopify_id) if shopify_id else "",
                meta={
                    "niche": product_type,
                    "cost": cost_bd,
                    "compare_at": compare_at,
                    "tags": tags,
                    "keywords": keys,
                    "image_urls": urls,
                    "research": r,
                    "shopify_handle": handle,
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
            "image_urls": urls,
            "chosen_niche": product_type,
        }

    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}
