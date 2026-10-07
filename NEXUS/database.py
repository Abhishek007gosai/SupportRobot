from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

import config

_client = AsyncIOMotorClient(config.MONGO_URI)
_db = _client[config.DB_NAME]

users = _db["users"]
settings = _db["settings"]
message_map = _db["message_map"]


# ---------- users ----------
async def add_user(user) -> bool:
    """Save user. Returns True if this is a brand new user."""
    result = await users.update_one(
        {"_id": user.id},
        {
            "$set": {"name": user.full_name, "username": user.username},
            "$setOnInsert": {"joined": datetime.now(timezone.utc)},
        },
        upsert=True,
    )
    return result.upserted_id is not None


async def remove_user(user_id: int) -> None:
    await users.delete_one({"_id": user_id})


async def count_users() -> int:
    return await users.count_documents({})


async def all_user_ids():
    async for doc in users.find({}, {"_id": 1}):
        yield doc["_id"]


# ---------- editable messages ----------
async def get_setting(key: str, default: str) -> str:
    doc = await settings.find_one({"_id": key})
    return doc["value"] if doc else default


async def set_setting(key: str, value: str) -> None:
    await settings.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)


async def reset_setting(key: str) -> None:
    await settings.delete_one({"_id": key})


# ---------- owner message -> user mapping (for replying) ----------
async def save_map(owner_msg_id: int, user_id: int) -> None:
    await message_map.update_one(
        {"_id": owner_msg_id}, {"$set": {"user_id": user_id}}, upsert=True
    )


async def get_mapped_user(owner_msg_id: int):
    doc = await message_map.find_one({"_id": owner_msg_id})
    return doc["user_id"] if doc else None
