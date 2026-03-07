from datetime import datetime, timezone
from auth.password import hash_password


async def seed_admin_user(db):
    """
    Seed the database with an admin user if it doesn't already exist.
    Runs on application startup.
    """
    admin_email = "admin@gmail.com"
    
    # Check if admin user already exists
    existing_admin = await db["users"].find_one({"email": admin_email})
    if existing_admin:
        print("✅  Admin user already exists. Skipping seed.")
        return
    
    # Create admin user
    now = datetime.now(timezone.utc)
    admin_user = {
        "name": "Arjun Kumar",
        "email": admin_email,
        "password": hash_password("admin@123"),
        "role": "admin",
        "created_at": now,
        "updated_at": now,
    }
    
    try:
        result = await db["users"].insert_one(admin_user)
        print(f"✅  Admin user seeded successfully with ID: {result.inserted_id}")
    except Exception as e:
        print(f"❌  Failed to seed admin user: {str(e)}")
