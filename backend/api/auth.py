# api/auth.py
from fastapi import APIRouter, HTTPException, Depends, Body
from passlib.context import CryptContext
from sqlmodel import Session, select

from core.db import get_session, load_users, save_users
from core.logger import get_logger
from core.security import create_access_token, create_refresh_token, decode_refresh_token
from models.db_models import IdentityUser, UserProfile
from models.user_models import UserRegister, UserLogin, Token, TokenRefreshRequest

logger = get_logger(__name__)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", status_code=200, response_model=dict)
def register(user: UserRegister):
    users = load_users()
    if any(u["username"] == user.username for u in users["users"]):
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(user.password)
    users["users"].append({
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password
    })
    save_users(users)
    return {"msg": "Registered"}

@router.post("/login", status_code=200, response_model=Token)
def login(user: UserLogin, session: Session = Depends(get_session)):
    users = load_users()
    found_user = next((u for u in users["users"] if u["username"] == user.username), None)

    if not found_user or not pwd_context.verify(user.password, found_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    subject = user.username
    issuer = "local-idp"

    # JIT provision to IdentityUser
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

        logger.info(f"Provisioned IdentityUser for subject: {subject} (issuer: {issuer})")

    # JIT provision to UserProfile (with username and email)
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == identity_user.id)
    ).first()

    if not profile:
        profile = UserProfile(
            user_id=identity_user.id,
            username=user.username,
            email=found_user.get("email", None),
            is_active=True,
            role="user"
        )
        session.add(profile)
        session.commit()

        logger.info(f"Provisioned UserProfile for user_id: {identity_user.id} ({user.username})")

    # Active check
    if not profile.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")

    # Generate tokens
    access_token = create_access_token({"sub": subject, "iss": issuer, "role": profile.role})
    refresh_token = create_refresh_token({"sub": subject, "iss": issuer, "role": profile.role})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", status_code=200, response_model=Token)
def refresh_token(data: TokenRefreshRequest = Body(...)):
    try:
        payload = decode_refresh_token(data.refresh_token)
        subject = payload.get("sub")
        issuer = payload.get("iss")
        role = payload.get("role", "user")
        if not subject or not issuer:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        new_access_token = create_access_token({"sub": subject, "iss": issuer, "role": role})
        return {
            "access_token": new_access_token,
            "refresh_token": data.refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
