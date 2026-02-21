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
    s = (title or "").strip()
    s = re.sub(r"\s*[–\-]\s*best price\s*\|\s*cash on delivery bd\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*\|\s*cash on delivery bd\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*\|\s*cod bd\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*[–\-]\s*.*\b(cod|delivery|bangladesh|bd)\b.*$", "", s, flags=re.I).strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s or (title or "product")


def _normalize_for_query(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# --- keyword helpers for strict validation ---
_IMG_STOP = {
    "best", "price", "cash", "delivery", "cod", "bd", "bangladesh", "premium", "quality",
    "buy", "order", "online", "store", "shop", "new", "original", "latest",
    "photo", "image", "product", "background", "isolated", "close", "up", "lifestyle",
    "packaging", "portable", "smart", "pro", "mini", "for", "with",
}

_BAD_ALT = {
    "peacock", "bird", "portrait", "model", "wedding", "baby", "cat", "dog",
    "landscape", "mountain", "ocean", "sunset", "flower", "nature",
    "man", "woman", "girl", "boy", "face", "people", "person", "selfie",
}

_NORM = {
    "earbuds": "earbud", "headphones": "headphone", "speakers": "speaker", "bottles": "bottle",
    "fans": "fan", "rollers": "roller", "watches": "watch", "chargers": "charger",
    "cables": "cable",
}


def _tokenize_img(s: str) -> List[str]:
    toks = re.findall(r"[a-z0-9]+", (s or "").lower())
    out: List[str] = []
    for t in toks:
        if len(t) <= 2:
            continue
        t = _NORM.get(t, t)
        if t not in out:
            out.append(t)
    return out


def _important_tokens(text: str) -> List[str]:
    toks = _tokenize_img(text)
    return [t for t in toks if t not in _IMG_STOP and not t.isdigit()]


def _alt_matches_product(product_title: str, alt: str | None) -> bool:
    """
    HARD LOCK:
    Image must contain the MAIN product noun.
    """

    if not alt:
        return False

    alt_l = alt.lower()
    title_l = product_title.lower()

    # Extract core nouns from title (important product words)
    important_words = [
        "fan", "speaker", "watch", "earbud", "earbuds", "headphone",
        "bottle", "roller", "ring light", "ring", "light",
        "sofa", "bedsheet", "sheet", "bed", "tripod",
        "keyboard", "mouse", "wallet", "charger",
        "power bank", "cable"
    ]

    # Special cases (multi-word products must match full phrase)
    if "ring light" in title_l:
        return "ring light" in alt_l

    if "power bank" in title_l:
        return "power bank" in alt_l

    # For all others: at least one strong product word must exist
    for word in important_words:
        if word in title_l:
            if word in alt_l:
                return True
            else:
                return False

    # fallback — if no known product word, allow
    return True


def _build_strict_product_query(title: str) -> str:
    raw = _normalize_for_query(_strip_seo_tail_for_images(title))

    # Remove marketing + generic commerce words
    stop = {
        "best", "price", "offer", "sale", "discount", "bd", "bangladesh", "cod",
        "delivery", "cash", "on", "available", "premium", "quality", "buy", "order",
        "online", "store", "shop", "new", "original", "latest", "for", "with",
        "smart", "pro", "mini", "portable", "newest"
    }

    tokens = re.findall(r"[a-z0-9]+", raw)
    tokens = [t for t in tokens if t not in stop and len(t) > 1]
    base = " ".join(tokens).strip() or raw or "product"

    # “infinite” rules (expandable)
    rules: List[Tuple[str, str]] = [
        (r"\bneck fan\b", "wearable neck fan"),
        (r"\bsmart watch\b", "smartwatch"),
        (r"\bsmartwatch\b", "smartwatch"),
        (r"\bearbuds\b", "wireless earbuds in ear"),
        (r"\bearbud\b", "wireless earbuds in ear"),
        (r"\bheadphones\b", "wireless headphones"),
        (r"\bheadphone\b", "wireless headphones"),
        (r"\bbluetooth speaker\b", "portable bluetooth speaker"),
        (r"\bspeaker\b", "portable bluetooth speaker"),
        (r"\bwater bottle\b", "water bottle"),
        (r"\bice roller\b", "ice roller for face"),
        (r"\bsofa cover\b", "sofa cover"),
        (r"\bsofa\b", "sofa furniture"),
        (r"\bpower bank\b", "power bank portable charger"),
        (r"\bring light\b", "ring light"),
        (r"\btripod\b", "phone tripod"),
        (r"\bphone holder\b", "phone holder stand"),
        (r"\bmouse\b", "computer mouse"),
        (r"\bkeyboard\b", "computer keyboard"),
        (r"\bwallet\b", "wallet"),
    ]

    for pat, forced in rules:
        if re.search(pat, raw):
            return forced

    # fallback: keep last 6 words max
    words = base.split()
    if len(words) > 6:
        base = " ".join(words[-6:])

    return base or "product"


def _image_urls(title: str, niche: str) -> List[str]:
    """
    ✅ STRICT:
    - Search by product title only
    - Accept only images whose ALT matches product keywords
    """
    core = _build_strict_product_query(title)

    # More strict product queries
    queries = [
        f"{core} product photo",
        f"{core} isolated on white background",
        f"{core} close up product",
        f"{core} product packshot",
        f"{core} product on table",
        f"{core} in hand product",
        f"{core} packaging product",
    ]

    urls: List[str] = []
    for q in queries:
        r = pexels_search_image(q, orientation="square")
        if r.get("ok") and r.get("image_url"):
            alt = r.get("alt") or ""
            if not _alt_matches_product(title, alt):
                # reject irrelevant image
                continue

            u = str(r["image_url"])
            if u not in urls:
                urls.append(u)

        if len(urls) >= 7:
            break

    return urls


def add_product_full_auto(
    niche: str | None = None,
    inventory_qty: int | None = None,
) -> Dict[str, Any]:
    raw_niche = (niche or getattr(settings, "STORE_NICHE", "") or "general").strip()
    niche_list = [x.strip() for x in raw_niche.split(",") if x.strip()]
    qty = int(inventory_qty or getattr(settings, "DEFAULT_INVENTORY_QTY", 100) or 100)

    if len(niche_list) <= 1:
        niche_guess = niche_list[0] if niche_list else "general"
        niche_final = _clean_product_type(niche_guess)
        r = find_winning_product_multisource(niche=niche_final)
    else:
        r = find_winning_product_multisource_for_many(niches=niche_list)
        niche_final = _clean_product_type(r.get("chosen_niche") or niche_list[0])

    if not r.get("ok"):
        return {"ok": False, "error": "live_research_failed", "details": r}

    product_type = _safe_product_type(niche_final)

    top = r["top_pick"]
    base_title = top.get("title") or "Product"
    short_desc = top.get("description") or "High-demand product for everyday use."
    cost_bd = float(top.get("suggested_cost") or 500.0)

    price, compare_at = _make_price_bd(cost_bd)

    seo_title = _seo_title_bd(base_title, product_type)
    keys = _keywords(seo_title, product_type)
    tags = _tags_from_keywords(keys)
    market_signals = (r.get("market_signals") or []) if isinstance(r, dict) else []
    body_html = _seo_description_bd(seo_title, product_type, short_desc, keys, market_signals)

    # ✅ IMPORTANT: use base_title to match the real product name
    urls = _image_urls(base_title, product_type)
    image_url = urls[0] if urls else None

    variants = _variants(seo_title, product_type, price, compare_at, qty)

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

    create_url = f"https://{settings.SHOPIFY_SHOP}/admin/api/{settings.SHOPIFY_API_VERSION}/products.json"

    payload: Dict[str, Any] = {
        "product": {
            "title": seo_title,
            "body_html": body_html,
            "vendor": settings.BRAND_NAME,
            "product_type": product_type,
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
