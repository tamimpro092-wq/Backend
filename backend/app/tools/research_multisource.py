from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Tuple

from sqlmodel import Session, select

from ..db import engine
from ..models import ProductDraft


# ===============================
# BIG CATALOG (2026 TRENDING)
# costs are in BDT-ish rough range
# ===============================

CATALOG: Dict[str, List[Dict[str, Any]]] = {
    # Fashion & Apparel
    "fashion": [
        {"base": "Men's Casual T-Shirt", "desc": "Comfort fit daily t-shirt, perfect for summer.", "cost": (250, 450)},
        {"base": "Women's Summer Dress", "desc": "Lightweight breathable dress for daily wear.", "cost": (450, 900)},
        {"base": "Slim Fit Jeans", "desc": "Modern slim fit jeans for everyday style.", "cost": (700, 1400)},
        {"base": "Hoodie Sweatshirt", "desc": "Soft hoodie for casual wear and travel.", "cost": (650, 1300)},
        {"base": "Leather Jacket Style Outerwear", "desc": "Trendy outerwear for premium look.", "cost": (1200, 2800)},
    ],

    # Beauty & Personal Care
    "beauty": [
        {"base": "Vitamin C Face Serum", "desc": "Glow boosting serum for brighter looking skin.", "cost": (350, 800)},
        {"base": "Matte Liquid Lipstick", "desc": "Long lasting matte lipstick with smooth finish.", "cost": (180, 450)},
        {"base": "Hair Growth Oil", "desc": "Nourishing oil for stronger healthier hair.", "cost": (250, 650)},
        {"base": "Organic Face Wash", "desc": "Gentle cleansing face wash for daily use.", "cost": (220, 520)},
        {"base": "Nail Art Kit", "desc": "DIY nail styling kit for salon-like nails.", "cost": (250, 600)},
        {"base": "Hair Straightening Brush", "desc": "Fast styling brush for smooth straight hair.", "cost": (750, 1600)},
        {"base": "Electric Makeup Brush Cleaner", "desc": "Clean makeup brushes quickly with spinning cleaner.", "cost": (650, 1400)},
    ],

    # Electronics & Gadgets / Phone Accessories / Smart Home
    "electronics": [
        {"base": "Wireless Bluetooth Earbuds", "desc": "Clear sound earbuds with charging case.", "cost": (700, 1500)},
        {"base": "Smart Watch", "desc": "Fitness tracking smartwatch with stylish design.", "cost": (900, 2200)},
        {"base": "Portable Power Bank", "desc": "Fast charging power bank for travel & office.", "cost": (650, 1600)},
        {"base": "LED Ring Light", "desc": "Perfect ring light for TikTok/Reels content.", "cost": (550, 1400)},
        {"base": "Mini Bluetooth Speaker", "desc": "Portable speaker with strong bass for its size.", "cost": (450, 1200)},
        {"base": "Wireless Charging Station", "desc": "All-in-one charging dock for desk setup.", "cost": (850, 1800)},
        {"base": "Smart Posture Corrector", "desc": "Wearable posture device that helps improve sitting posture.", "cost": (900, 1900)},
        {"base": "LED Galaxy Projector", "desc": "Aesthetic galaxy light projector for room decor.", "cost": (850, 2000)},
        {"base": "Smart Home Plug (WiFi)", "desc": "Control devices with mobile app and timer.", "cost": (450, 1100)},
    ],

    # Home & Kitchen / Organization
    "home": [
        {"base": "Vegetable Chopper", "desc": "Fast chopping tool for kitchen prep.", "cost": (350, 900)},
        {"base": "Non-Stick Frying Pan", "desc": "Easy cook non-stick pan with durable coating.", "cost": (700, 1600)},
        {"base": "Storage Organizer Box", "desc": "Home organization box for clean space.", "cost": (350, 900)},
        {"base": "LED Wall Clock", "desc": "Modern LED wall clock for home decor.", "cost": (750, 1800)},
        {"base": "Bedsheet Set", "desc": "Soft bedsheet set for premium sleep feel.", "cost": (900, 2200)},
        {"base": "LED Motion Sensor Light", "desc": "Auto light for stairs, hallway and closet.", "cost": (300, 900)},
        {"base": "Eco-Friendly Reusable Storage Bags", "desc": "Reusable bags for kitchen and meal prep.", "cost": (350, 850)},
    ],

    # Health & Fitness / Pain Relief
    "fitness": [
        {"base": "Yoga Mat", "desc": "Non-slip mat for home workouts and yoga.", "cost": (450, 1100)},
        {"base": "Resistance Bands Set", "desc": "Home workout bands for full body training.", "cost": (450, 950)},
        {"base": "Waist Trainer Belt", "desc": "Support belt for posture and waist shaping.", "cost": (450, 1100)},
        {"base": "Protein Shaker Bottle", "desc": "Mix protein easily, perfect for gym.", "cost": (220, 520)},
        {"base": "Heated Knee Massager", "desc": "Pain relief massager for knee comfort.", "cost": (1500, 3200)},
        {"base": "Electric Foot Massager", "desc": "Relaxing foot massager for daily comfort.", "cost": (1600, 3500)},
        {"base": "Anti-Snoring Device", "desc": "Simple solution product for better sleep.", "cost": (600, 1500)},
    ],

    # Baby & Kids
    "baby": [
        {"base": "Baby Romper", "desc": "Soft comfy romper for babies.", "cost": (350, 850)},
        {"base": "Kids Educational Toy", "desc": "Learning toy for early development.", "cost": (450, 1100)},
        {"base": "Baby Feeding Bottle", "desc": "Safe feeding bottle for newborns.", "cost": (250, 650)},
        {"base": "Cartoon School Bag", "desc": "Cute bag for kids school use.", "cost": (650, 1400)},
        {"base": "Baby Safety Lock Set", "desc": "Home safety locks for baby proofing.", "cost": (350, 900)},
    ],

    # Jewelry & Accessories
    "jewelry": [
        {"base": "Gold Plated Necklace", "desc": "Elegant necklace for daily and party wear.", "cost": (350, 900)},
        {"base": "Fashion Bracelet", "desc": "Stylish bracelet for modern look.", "cost": (220, 520)},
        {"base": "Stud Earrings", "desc": "Minimal stud earrings for everyday wear.", "cost": (180, 450)},
        {"base": "Women's Handbag", "desc": "Trendy handbag for daily use.", "cost": (900, 2200)},
        {"base": "Sunglasses UV Protection", "desc": "UV sunglasses for outdoor use.", "cost": (350, 950)},
    ],

    # Footwear
    "footwear": [
        {"base": "Running Shoes", "desc": "Lightweight running shoes for comfort.", "cost": (900, 2200)},
        {"base": "Casual Sneakers", "desc": "Everyday sneakers for men and women.", "cost": (850, 2000)},
        {"base": "Leather Sandals", "desc": "Comfort sandals for daily wear.", "cost": (650, 1600)},
        {"base": "High Heel Shoes", "desc": "Stylish heels for party wear.", "cost": (850, 2200)},
        {"base": "Comfort Slippers", "desc": "Soft slippers for home use.", "cost": (250, 650)},
    ],

    # Pet Supplies
    "pet": [
        {"base": "Pet Hair Remover Roller", "desc": "Remove pet hair from sofa and clothes easily.", "cost": (350, 850)},
        {"base": "Dog Leash", "desc": "Strong leash for safe walking.", "cost": (250, 650)},
        {"base": "Cat Scratching Post", "desc": "Scratching post to protect furniture.", "cost": (650, 1600)},
        {"base": "Pet Grooming Brush", "desc": "Brush for comfortable grooming.", "cost": (220, 520)},
        {"base": "Automatic Pet Feeder", "desc": "Timed feeder for busy pet owners.", "cost": (1800, 3800)},
    ],

    # Automotive / Car Accessories
    "automotive": [
        {"base": "Magnetic Car Phone Holder", "desc": "Hands-free phone mount for driving.", "cost": (250, 650)},
        {"base": "Car Vacuum Cleaner Mini", "desc": "Portable vacuum for car cleaning.", "cost": (850, 2200)},
        {"base": "Car Gap Filler Organizer", "desc": "Stops items falling into seat gap.", "cost": (250, 650)},
        {"base": "Seat Covers Set", "desc": "Protect seats and upgrade interior look.", "cost": (1200, 3200)},
        {"base": "Car Cleaning Kit", "desc": "Complete cleaning kit for car interior.", "cost": (650, 1600)},
    ],

    # Office & Stationery
    "office": [
        {"base": "Desk Organizer", "desc": "Keep desk neat with storage compartments.", "cost": (350, 900)},
        {"base": "Laptop Stand", "desc": "Ergonomic stand for better posture.", "cost": (650, 1600)},
        {"base": "Spiral Notebook Set", "desc": "Quality notebooks for study and office.", "cost": (220, 520)},
        {"base": "Gel Pen Set", "desc": "Smooth writing pens for daily use.", "cost": (180, 450)},
    ],

    # Sports & Outdoor
    "outdoor": [
        {"base": "Camping Tent", "desc": "Easy setup tent for outdoor trips.", "cost": (1800, 4200)},
        {"base": "Hiking Backpack", "desc": "Comfort backpack for travel & hiking.", "cost": (900, 2400)},
        {"base": "Cycling Helmet", "desc": "Safety helmet for cycling.", "cost": (850, 2200)},
        {"base": "Water Bottle (Sports)", "desc": "Reusable bottle for gym and travel.", "cost": (220, 520)},
    ],

    # General fallback
    "general": [
        {"base": "Portable Neck Fan", "desc": "Hands-free cooling fan for summer heat.", "cost": (650, 1500)},
        {"base": "Waterproof Bluetooth Speaker", "desc": "Outdoor-friendly speaker for travel.", "cost": (750, 1800)},
        {"base": "Ice Roller for Face", "desc": "Cooling ice roller for skincare routine.", "cost": (250, 650)},
    ],
}

ADJECTIVES = ["Premium", "Pro", "Ultra", "Smart", "Compact", "Portable", "Modern", "Heavy-Duty"]
MARKET_SIGNALS = [
    "Solves a real problem (high conversion)",
    "Lightweight & cheap shipping",
    "Looks good in video ads (Reels/TikTok)",
    "High perceived value for COD buyers",
    "Evergreen demand + repeat purchase potential",
]


def _normalize_niche(niche: str) -> str:
    s = (niche or "general").strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"\s+", " ", s)

    # map common words into catalog keys
    mapping = {
        "apparel": "fashion",
        "clothing": "fashion",
        "fashion and apparel": "fashion",
        "skincare": "beauty",
        "personal care": "beauty",
        "gadgets": "electronics",
        "phone accessories": "electronics",
        "smart home": "electronics",
        "home and kitchen": "home",
        "kitchen": "home",
        "home decor": "home",
        "home organization": "home",
        "pain relief": "fitness",
        "health": "fitness",
        "health and fitness": "fitness",
        "baby and kids": "baby",
        "kids": "baby",
        "jewelry and accessories": "jewelry",
        "accessories": "jewelry",
        "car accessories": "automotive",
        "automotive": "automotive",
        "sports and outdoor": "outdoor",
        "sports": "outdoor",
        "outdoor": "outdoor",
        "stationery": "office",
    }
    return mapping.get(s, s if s in CATALOG else "general")


def _recent_titles(limit: int = 150) -> List[str]:
    try:
        with Session(engine) as session:
            rows = session.exec(
                select(ProductDraft.title).order_by(ProductDraft.created_at.desc()).limit(limit)
            ).all()
            return [r for r in rows if r]
    except Exception:
        return []


def _pick_unique_from_pool(pool: List[Dict[str, Any]], recent_titles: set[str]) -> Dict[str, Any]:
    # try many times to avoid repetition
    for _ in range(60):
        item = random.choice(pool)
        base = item["base"].strip()

        # add variation sometimes
        title = base
        if random.random() < 0.60:
            title = f"{random.choice(ADJECTIVES)} {base}"

        if title.lower() in recent_titles:
            continue

        lo, hi = item.get("cost", (400, 900))
        cost = float(random.randint(int(lo), int(hi)))

        return {
            "title": title,
            "description": item["desc"].strip(),
            "suggested_cost": cost,
            "source": "internal_catalog",
        }

    # if everything repeats, still return something
    item = random.choice(pool)
    lo, hi = item.get("cost", (400, 900))
    return {
        "title": f"{random.choice(ADJECTIVES)} {item['base']}".strip(),
        "description": item["desc"].strip(),
        "suggested_cost": float(random.randint(int(lo), int(hi))),
        "source": "internal_catalog",
    }


def find_winning_product_multisource(niche: str = "general") -> Dict[str, Any]:
    niche_key = _normalize_niche(niche)
    pool = CATALOG.get(niche_key) or CATALOG["general"]

    recent = set(t.lower().strip() for t in _recent_titles(150))
    top = _pick_unique_from_pool(pool, recent)

    return {
        "ok": True,
        "chosen_niche": niche_key,
        "sources_used": ["internal_catalog"],
        "top_pick": {
            "title": top["title"],
            "description": top["description"],
            "suggested_cost": top["suggested_cost"],
            "source": top["source"],
            "confirmed": False,
        },
        "market_signals": random.sample(MARKET_SIGNALS, k=3),
    }


def find_winning_product_multisource_for_many(niches: List[str]) -> Dict[str, Any]:
    niches = [x.strip() for x in (niches or []) if x and x.strip()]
    if not niches:
        return find_winning_product_multisource("general")

    # Try each niche until we find a non-repeating pick
    recent = set(t.lower().strip() for t in _recent_titles(150))
    random.shuffle(niches)

    for n in niches:
        niche_key = _normalize_niche(n)
        pool = CATALOG.get(niche_key) or CATALOG["general"]
        top = _pick_unique_from_pool(pool, recent)
        if top.get("title"):
            return {
                "ok": True,
                "chosen_niche": niche_key,
                "sources_used": ["internal_catalog"],
                "top_pick": {
                    "title": top["title"],
                    "description": top["description"],
                    "suggested_cost": top["suggested_cost"],
                    "source": top["source"],
                    "confirmed": False,
                },
                "market_signals": random.sample(MARKET_SIGNALS, k=3),
            }

    return find_winning_product_multisource("general")
