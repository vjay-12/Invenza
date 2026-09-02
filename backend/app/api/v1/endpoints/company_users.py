import uuid
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import get_password_hash
from app.api.deps import require_admin
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.schemas.user import (
    CompanyUserCreate,
    CompanyUserUpdate,
    UserResponse,
)
from app.services.email_service import EmailService

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def list_company_users(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Company Admin: List all team members belonging to this company.
    """
    res = await db.execute(
        select(User).where(User.tenant_id == current_admin.tenant_id).order_by(User.created_at.desc())
    )
    return res.scalars().all()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_company_user(
    user_in: CompanyUserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Company Admin: Create a new user (Manager, Staff, Viewer) for this company.
    Dispatches login credentials to the user's email.
    """
    email_clean = user_in.email.strip().lower()

    # Check email uniqueness globally
    existing = await db.execute(select(User).where(User.email == email_clean))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email_clean}' already exists.",
        )

    # Get company name for email
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == current_admin.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    company_name = tenant.name if tenant else "Your Company"

    new_user = User(
        id=uuid.uuid4(),
        tenant_id=current_admin.tenant_id,
        email=email_clean,
        full_name=user_in.full_name.strip(),
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role.lower().strip(),
        permissions=user_in.permissions,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Dispatch welcome email with credentials
    if user_in.send_email:
        await EmailService.send_staff_user_credentials(
            company_name=company_name,
            user_name=new_user.full_name,
            user_email=new_user.email,
            temporary_password=user_in.password,
            role=new_user.role,
            permissions=new_user.permissions,
        )

    return new_user

@router.put("/{user_id}", response_model=UserResponse)
async def update_company_user(
    user_id: UUID,
    user_update: CompanyUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Company Admin: Update a user's role, permissions, or active status.
    """
    res = await db.execute(
        select(User).where(and_(User.id == user_id, User.tenant_id == current_admin.tenant_id))
    )
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this company")

    if user_update.full_name is not None:
        user.full_name = user_update.full_name.strip()
    if user_update.role is not None:
        user.role = user_update.role.lower().strip()
    if user_update.permissions is not None:
        user.permissions = user_update.permissions
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Company Admin: Remove a user from this company.
    """
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    res = await db.execute(
        select(User).where(and_(User.id == user_id, User.tenant_id == current_admin.tenant_id))
    )
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this company")

    await db.delete(user)
    await db.commit()
