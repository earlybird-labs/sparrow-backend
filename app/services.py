# services.py

from .database import Database
from .schema import UserSchema
from bson.objectid import ObjectId

db = Database.get_instance()


def create_db_thread(channel_id, ts, oai_thread, vectorstore_id=None):
    return db.threads.insert_one(
        {
            "channel_id": channel_id,
            "ts": ts,
            "oai_thread": oai_thread,
            "vectorstore_id": vectorstore_id,
            "num_files": 0,
        }
    )


def update_thread(thread_id, update_obj):
    return db.threads.update_one({"_id": thread_id}, {"$set": update_obj})


def find_db_thread(channel_id, ts):
    return db.threads.find_one({"channel_id": channel_id, "ts": ts})


def find_db_thread_by_id(thread_id):
    if type(thread_id) == str:
        return db.threads.find_one({"_id": ObjectId(thread_id)})
    else:
        return db.threads.find_one({"_id": thread_id})


def add_vectorstore_id_to_thread(thread_id, vectorstore_id):
    if type(thread_id) == str:
        return db.threads.update_one(
            {"_id": ObjectId(thread_id)}, {"$set": {"vectorstore_id": vectorstore_id}}
        )
    else:
        return db.threads.update_one(
            {"_id": thread_id}, {"$set": {"vectorstore_id": vectorstore_id}}
        )


def create_user(slack_user_id, name, email):
    user = {
        "name": name,
        "slack_user_id": slack_user_id,
        "email": email,
    }

    db.users.insert_one(user)


def get_user_information(slack_user_id):
    return db.users.find_one({"slack_user_id": slack_user_id})


if __name__ == "__main__":
    # create_user("U05960Z874N", "Joe Petrantoni", "joe@earlybirdlabs.io")
    user = get_user_information("U05960Z874N")
    print(UserSchema(**user))
