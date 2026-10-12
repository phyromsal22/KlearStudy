from datetime import datetime, timedelta, timezone
import os

import jwt

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from pwdlib import PasswordHash

from database.database import get_db
from database.models import User


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# PASSWORD HASHING
# ============================================================

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# JWT CONFIGURATION
# ============================================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()

if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing or too short. "
        "Set a random secret of at least 32 characters in backend/.env."
    )

JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# ============================================================
# JWT SECURITY
# ============================================================

security = HTTPBearer(
    auto_error=False,
)


# ============================================================
# REQUEST MODELS
# ============================================================

class RegisterRequest(BaseModel):

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
    )

    phone_number: str = Field(
        ...,
        min_length=8,
        max_length=20,
    )

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):

    phone_number: str = Field(
        ...,
        min_length=8,
        max_length=20,
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_username(
    username: str,
) -> str:

    return username.strip().lower()


def normalize_phone(
    phone_number: str,
) -> str:

    value = phone_number.strip()

    if value.startswith("+"):

        return (
            "+"
            + "".join(
                character
                for character in value[1:]
                if character.isdigit()
            )
        )

    return "".join(
        character
        for character in value
        if character.isdigit()
    )


# ============================================================
# JWT CREATE
# ============================================================

def create_access_token(
    user_id: int,
) -> str:

    now = datetime.now(
        timezone.utc
    )

    expire = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return token


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db),
) -> User:

    # ========================================================
    # CHECK TOKEN
    # ========================================================

    if credentials is None:

        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    token = credentials.credentials

    # ========================================================
    # DECODE JWT
    # ========================================================

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Token has expired.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # ========================================================
    # CHECK TOKEN TYPE
    # ========================================================

    if payload.get("type") != "access":

        raise HTTPException(
            status_code=401,
            detail="Invalid token type.",
        )

    # ========================================================
    # GET USER ID
    # ========================================================

    subject = payload.get("sub")

    if not subject:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )

    try:

        user_id = int(subject)

    except (TypeError, ValueError):

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )

    # ========================================================
    # FIND USER
    # ========================================================

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="User not found.",
        )

    # ========================================================
    # CHECK ACTIVE
    # ========================================================

    if not user.is_active:

        raise HTTPException(
            status_code=403,
            detail="User account is inactive.",
        )

    return user


# ============================================================
# REGISTER
# ============================================================

@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):

    username = normalize_username(
        request.username
    )

    phone_number = normalize_phone(
        request.phone_number
    )

    full_name = request.full_name.strip()

    # ========================================================
    # VALIDATION
    # ========================================================

    if not username:

        raise HTTPException(
            status_code=400,
            detail="Username is required.",
        )

    if not phone_number:

        raise HTTPException(
            status_code=400,
            detail="Phone number is required.",
        )

    if not full_name:

        raise HTTPException(
            status_code=400,
            detail="Full name is required.",
        )

    if len(phone_number) < 8:

        raise HTTPException(
            status_code=400,
            detail="Invalid phone number.",
        )

    # ========================================================
    # CHECK USERNAME
    # ========================================================

    existing_username = (
        db.query(User)
        .filter(
            User.username == username
        )
        .first()
    )

    if existing_username:

        raise HTTPException(
            status_code=409,
            detail="Username already exists.",
        )

    # ========================================================
    # CHECK PHONE
    # ========================================================

    existing_phone = (
        db.query(User)
        .filter(
            User.phone_number == phone_number
        )
        .first()
    )

    if existing_phone:

        raise HTTPException(
            status_code=409,
            detail="Phone number already exists.",
        )

    # ========================================================
    # HASH PASSWORD
    # ========================================================

    try:

        hashed_password = hash_password(
            request.password
        )

    except Exception as error:

        print(
            f"❌ Password hashing failed: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Password hashing failed.",
        )

    # ========================================================
    # CREATE USER
    # ========================================================

    user = User(
        username=username,
        phone_number=phone_number,
        password_hash=hashed_password,
        full_name=full_name,
        is_active=True,
    )

    db.add(user)

    # ========================================================
    # SAVE
    # ========================================================

    try:

        db.commit()

        db.refresh(user)

    except Exception as error:

        db.rollback()

        print(
            f"❌ User registration failed: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to create user.",
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "success": True,
        "message": "User registered successfully.",
        "user": {
            "id": user.id,
            "username": user.username,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else None
            ),
        },
    }


# ============================================================
# LOGIN
# ============================================================

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    phone_number = normalize_phone(
        request.phone_number
    )

    # ========================================================
    # FIND USER
    # ========================================================

    user = (
        db.query(User)
        .filter(
            User.phone_number == phone_number
        )
        .first()
    )

    # ========================================================
    # GENERIC LOGIN ERROR
    # ========================================================

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password.",
        )

    # ========================================================
    # CHECK ACTIVE
    # ========================================================

    if not user.is_active:

        raise HTTPException(
            status_code=403,
            detail="User account is inactive.",
        )

    # ========================================================
    # VERIFY PASSWORD
    # ========================================================

    try:

        valid_password = verify_password(
            request.password,
            user.password_hash,
        )

    except Exception as error:

        print(
            f"❌ Password verification failed: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Password verification failed.",
        )

    if not valid_password:

        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password.",
        )

    # ========================================================
    # CREATE TOKEN
    # ========================================================

    access_token = create_access_token(
        user.id
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "success": True,
        "message": "Login successful.",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "is_active": user.is_active,
        },
    }


# ============================================================
# GET CURRENT USER
# ============================================================

@router.get("/me")
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):

    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "phone_number": current_user.phone_number,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "created_at": (
                current_user.created_at.isoformat()
                if current_user.created_at
                else None
            ),
            "updated_at": (
                current_user.updated_at.isoformat()
                if current_user.updated_at
                else None
            ),
        },
    }


# ============================================================
# LOGOUT
# ============================================================

@router.post("/logout")
def logout(
    current_user: User = Depends(
        get_current_user
    ),
):

    return {
        "success": True,
        "message": "Logout successful. Remove the access token on the client.",
        "user_id": current_user.id,
    }


# ============================================================
# PASSWORD TEST
# ============================================================

@router.post("/password-test")
def password_test():

    test_password = "12345678"

    hashed = hash_password(
        test_password
    )

    verified = verify_password(
        test_password,
        hashed,
    )

    return {
        "success": True,
        "hashing": True,
        "verification": verified,
    }