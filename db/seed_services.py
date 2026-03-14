from datetime import datetime, timezone
from uuid import uuid4


SERVICES = [
    {
        "service_name": "Delivery",
        "description": "Home delivery within city limits",
        "pricing": "₹30 - ₹80",
        "coverage_area": "15 zones",
        "is_active": True,
    },
    {
        "service_name": "Takeaway",
        "description": "Quick pickup from restaurant",
        "pricing": "No extra charge",
        "coverage_area": "All outlets",
        "is_active": True,
    },
    {
        "service_name": "Dine-in",
        "description": "In-restaurant dining experience",
        "pricing": "Menu price",
        "coverage_area": "3 outlets",
        "is_active": True,
    },
    {
        "service_name": "Catering",
        "description": "Catering for events and parties",
        "pricing": "₹350/plate onwards",
        "coverage_area": "City-wide",
        "is_active": True,
    },
    {
        "service_name": "Event Services",
        "description": "Full event management with food",
        "pricing": "Custom pricing",
        "coverage_area": "On request",
        "is_active": False,
    },
    {
        "service_name": "Subscription Meals",
        "description": "Weekly/monthly meal plans",
        "pricing": "₹2,999/mo",
        "coverage_area": "10 zones",
        "is_active": True,
    },
    {
        "service_name": "Corporate Orders",
        "description": "Bulk orders for offices",
        "pricing": "₹150/head onwards",
        "coverage_area": "Business district",
        "is_active": True,
    },
]


async def seed_services(db):
    """
    Seeds the services collection on startup.
    Skips any service that already exists by name — safe to run multiple times.
    """
    inserted = 0
    skipped = 0

    for service in SERVICES:
        existing = await db["services"].find_one({"service_name": service["service_name"]})
        if existing:
            skipped += 1
            continue

        now = datetime.now(timezone.utc)
        await db["services"].insert_one({
            "service_id": f"SRV-{uuid4().hex[:8].upper()}",
            **service,
            "created_at": now,
            "updated_at": now,
        })
        inserted += 1

    if inserted:
        print(f"✅  Seeded {inserted} services.")
    if skipped:
        print(f"⏭️   Skipped {skipped} already existing services.")