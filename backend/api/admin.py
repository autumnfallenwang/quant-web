# api/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from models.db_models import UserProfile, IdentityUser
from models.user_models import UserProfileOut, UserProvisioningRequest, UserProfileUpdate
from core.db import get_session
from core.security import require_admin

router = APIRouter()

@router.get("/users", status_code=200, response_model=list[UserProfileOut])
def list_users(
    admin: UserProfile = Depends(require_admin),
    session: Session = Depends(get_session)
):
    return session.exec(select(UserProfile)).all()

@router.post("/users", status_code=200, response_model=UserProfileOut)
def provision_user(
    req: UserProvisioningRequest,
    admin: UserProfile = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # Check if IdentityUser exists
    identity_user = session.exec(
        select(IdentityUser).where(
            (IdentityUser.subject == req.subject) &
            (IdentityUser.issuer == req.issuer)
        )
    ).first()

    if identity_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Create IdentityUser
    identity_user = IdentityUser(subject=req.subject, issuer=req.issuer)
    session.add(identity_user)
    session.commit()
    session.refresh(identity_user)

    # Create UserProfile
    profile = UserProfile(
        user_id=identity_user.id,
        username=req.username,
        email=req.email,
        is_active=req.is_active,
        role=req.role
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)

    return profile

@router.patch("/users/{user_id}", status_code=200, response_model=UserProfileOut)
def update_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    admin: UserProfile = Depends(require_admin),
    session: Session = Depends(get_session)
):
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    session.add(profile)
    session.commit()
    session.refresh(profile)

    return profile

@router.delete("/users/{user_id}", status_code=200, response_model=dict)
def delete_user(
    user_id: int,
    admin: UserProfile = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # Fetch both IdentityUser and UserProfile
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()
    
    user = session.exec(
        select(IdentityUser).where(IdentityUser.id == user_id)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="IdentityUser not found")

    # Delete profile if exists
    if profile:
        session.delete(profile)

    # Delete identity user
    session.delete(user)
    session.commit()

    return {"msg": f"User {user_id} deleted successfully"}
