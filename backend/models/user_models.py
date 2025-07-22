# models/user_models.py
from typing import Optional
from datetime import datetime

from pydantic import BaseModel

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserProfileOut(BaseModel):
    id: int
    user_id: int
    username: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# For provisioning a brand new user (creates IdentityUser + UserProfile)
class UserProvisioningRequest(BaseModel):
    subject: str
    issuer: str = "local-idp"
    username: str
    email: Optional[str]
    is_active: bool = True
    role: str = "user"

# For updating profile fields (on existing user)
class UserProfileUpdate(BaseModel):
    email: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class UserProfileCreate(BaseModel):
    user_id: int
    username: str
    email: Optional[str] = None
    role: str = "user"
    is_active: bool = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str
