from .config import MONGODB_URI, MONGODB_DB
from pymongo import MongoClient


# MongoDB class to manage MongoDB connections
class MongoDB:
    # Singleton instance of MongoDB
    _instance = None

    # Static method to get the singleton instance of MongoDB
    @staticmethod
    def get_instance():
        # If instance is not created, create one
        if MongoDB._instance is None:
            # Get the configuration
            try:
                # Try to create a MongoDB instance
                MongoDB._instance = MongoClient(MONGODB_URI)[MONGODB_DB]
            except Exception as e:
                # If SSL handshake fails, attempt to reconnect
                if "SSL handshake failed" in str(e):
                    print("SSL handshake failed, attempting to reconnect...")
                    # Attempt to reconnect
                    MongoDB._instance = MongoClient(MONGODB_URI)[MONGODB_DB]
        # Return the singleton instance
        return MongoDB._instance


if __name__ == "__main__":
    # Instantiate the MongoDB service
    mongodb_service = MongoDB.get_instance()
    # Print the instance for testing
    print(mongodb_service)
