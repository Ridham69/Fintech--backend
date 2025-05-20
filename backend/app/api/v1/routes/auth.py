from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Dict, Optional

router = APIRouter(tags=["authentication"])

# OAuth2 password bearer for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# Mock user database - replace with real database in production
fake_users_db = {
    "testuser": {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "fakehashedtestpass",  # In production, use proper password hashing
        "disabled": False,
    }
}

def fake_hash_password(password: str) -> str:
    """
    Mock password hashing function.
    In production, use a proper password hashing library like passlib.
    """
    return f"fakehashed{password}"

def fake_verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Mock password verification function.
    In production, use a proper password verification method.
    """
    return hashed_password == fake_hash_password(plain_password)

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user by username and password.
    Returns the user if authentication is successful, None otherwise.
    """
    if username not in fake_users_db:
        return None
    user = fake_users_db[username]
    if not fake_verify_password(password, user["hashed_password"]):
        return None
    return user

def create_access_token(data: Dict) -> str:
    """
    Create a JWT access token.
    In production, use a proper JWT library like python-jose.
    """
    # This is a placeholder - implement real JWT token creation
    return f"fake-jwt-token-for-{data['sub']}"

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get the current user from the JWT token.
    In production, implement proper JWT validation.
    """
    # This is a placeholder - implement real JWT token validation
    if not token or not token.startswith("fake-jwt-token-for-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = token.replace("fake-jwt-token-for-", "")
    if username not in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return fake_users_db[username]

async def get_current_active_user(current_user: Dict = Depends(get_current_user)):
    """
    Get the current active user.
    Checks if the user is disabled.
    """
    if current_user.get("disabled"):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/login", response_model=Dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and provide JWT token.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token({"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(username: str, email: str, password: str):
    """
    Register a new user.
    In production, implement proper user registration with database storage.
    """
    if username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # In production, store user in a real database
    # This is just a placeholder implementation
    hashed_password = fake_hash_password(password)
    fake_users_db[username] = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "disabled": False,
    }
    
    return {"message": f"User {username} created successfully"}

@router.get("/me", response_model=Dict)
async def read_users_me(current_user: Dict = Depends(get_current_active_user)):
    """
    Get information about the currently authenticated user.
    """
    # Don't return the hashed password
    user_info = {k: v for k, v in current_user.items() if k != "hashed_password"}
    return user_info
