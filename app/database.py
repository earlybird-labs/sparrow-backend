# database.py

from typing import Dict, Any, Optional
from pymongo import MongoClient
from bson import ObjectId
from .config import MONGODB_DB, MONGODB_URI


class Database:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DB]
        self.threads_collection = self.db["threads"]
        self.users_collection = self.db["users"]

    def create_db_thread(self, channel: str, thread_ts: str) -> ObjectId:
        thread_data = {
            "channel": channel,
            "thread_ts": thread_ts,
            "num_files": 0,
        }
        return self.threads_collection.insert_one(thread_data)

    def find_db_thread(self, channel: str, thread_ts: str) -> Optional[Dict[str, Any]]:
        return self.threads_collection.find_one(
            {"channel": channel, "thread_ts": thread_ts}
        )

    def find_db_thread_by_id(self, thread_id: ObjectId) -> Optional[Dict[str, Any]]:
        return self.threads_collection.find_one({"_id": thread_id})

    def add_user(self, user_id: str, access_token: str) -> None:
        self.users_collection.insert_one(
            {"slack_user_id": user_id, "slack_access_token": access_token}
        )

    def update_thread(
        self, thread: Dict[str, Any], update_data: Dict[str, Any]
    ) -> None:
        self.threads_collection.update_one(
            {"_id": thread["_id"]}, {"$set": update_data}
        )


db = Database()
