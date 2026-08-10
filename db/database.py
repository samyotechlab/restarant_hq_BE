from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings
from db.seed_services import seed_services as seed_services
from db.seed import seed_admin_user

client: AsyncIOMotorClient
db = None


async def connect_db():
    """Called on app startup — creates the Motor client and selects the DB."""
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL, tlsAllowInvalidCertificates=True, tz_aware=True)
    db_name = settings.MONGODB_URL.split("/")[-1].split("?")[0]
    db = client[db_name]
    print(f"✅  Connected to MongoDB")
    
    # Seed admin user on startup
    await seed_admin_user(db)
    # await seed_services(db)


async def close_db():
    """Called on app shutdown — closes the Motor client."""
    global client
    if client:
        client.close()
        print("🔌  MongoDB connection closed.")


def get_db():
    """Dependency injector that returns the active database handle."""
    return db
