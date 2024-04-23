from .database import MongoDB
from .schema import UserSchema

db = MongoDB.get_instance()


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
