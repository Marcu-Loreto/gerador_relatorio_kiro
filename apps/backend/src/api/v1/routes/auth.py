"""Authentication routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.logging import get_logger
from src.core.security import create_access_token, get_password_hash, verify_password

logger = get_logger(__name__)
router = APIRouter()

# Demo users (use DB in production)
demo_users = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("admin123"),
        "role": "admin",
    },
    "user": {
        "username": "user",
        "hashed_password": get_password_hash("user123"),
        "role": "user",
    },
}


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = demo_users.get(request.username)

    if not user or not verify_password(request.password, user["hashed_password"]):
        logger.warning("login_failed", username=request.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )

    logger.info("login_success", username=request.username)

    return TokenResponse(
        access_token=token,
        username=user["username"],
        role=user["role"],
    )
