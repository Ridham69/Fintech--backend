# Example FastAPI dependency
from fastapi import Depends

def get_current_user():
    # Replace with real logic
    return {"username": "mockuser"}