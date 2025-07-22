# core/security.py
import os
import json
from datetime import datetime, timedelta, UTC

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from cryptography.fernet import Fernet
from sqlmodel import Session, select

from core.settings import settings
from core.db import get_session
from models.db_models import IdentityUser, UserProfile

# export environment variables
TOKEN_ALGORITHM = settings.TOKEN_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
ACCESS_TOKEN_SECRET_KEY = settings.ACCESS_TOKEN_SECRET_KEY
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_SECRET_KEY = settings.REFRESH_TOKEN_SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Load key from env var or fallback to local file (dev only)
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    # DEV ONLY fallback — generate once and reuse
    key_file = ".fernet.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            FERNET_KEY = f.read()
    else:
        FERNET_KEY = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(FERNET_KEY)

fernet = Fernet(FERNET_KEY)

def encrypt_str(raw_str: str) -> str:
    return fernet.encrypt(raw_str.encode()).decode()

def decrypt_str(encrypted_str: str) -> str:
    return fernet.decrypt(encrypted_str.encode()).decode()

def encrypt_dict(raw_dict: dict) -> str:
    raw_json = json.dumps(raw_dict)
    return fernet.encrypt(raw_json.encode()).decode()

def decrypt_dict(encrypted_dict: str) -> dict:
    decrypted_json = fernet.decrypt(encrypted_dict.encode()).decode()
    return json.loads(decrypted_json)

def create_token(data: dict, expires_delta: timedelta, secret_key: str):
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=TOKEN_ALGORITHM)

def create_access_token(data: dict):
    return create_token(
        data,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        ACCESS_TOKEN_SECRET_KEY
    )

def create_refresh_token(data: dict):
    return create_token(
        data,
        timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
        REFRESH_TOKEN_SECRET_KEY
    )

def decode_token(token: str, secret_key: str):
    return jwt.decode(token, secret_key, algorithms=[TOKEN_ALGORITHM])

def decode_access_token(token: str):
    return decode_token(token, ACCESS_TOKEN_SECRET_KEY)

def decode_refresh_token(token: str):
    return decode_token(token, REFRESH_TOKEN_SECRET_KEY)

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        issuer = payload.get("iss", "local-idp")

        if not subject:
            raise HTTPException(status_code=401, detail="Unauthorized")
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    identity_user = session.exec(
        select(IdentityUser).where(
            (IdentityUser.subject == subject) &
            (IdentityUser.issuer == issuer)
        )
    ).first()

    if not identity_user:
        identity_user = IdentityUser(subject=subject, issuer=issuer)
        session.add(identity_user)
        session.commit()
        session.refresh(identity_user)

    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == identity_user.id)
    ).first()

    if not profile:
        profile = UserProfile(
            user_id=identity_user.id,
            username=subject,
            is_active=True,
            role="user"
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)

    if not profile.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return profile

def require_admin(user: UserProfile = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user