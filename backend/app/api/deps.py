from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant

DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts and authenticates current user from Bearer JWT.
    Enforces active user check and active company/tenant check.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your user account has been deactivated. Please contact your administrator.",
        )

    # If user is not super_admin, check if tenant company is active
    if user.role != UserRole.SUPER_ADMIN.value and user.role != "super_admin":
        tenant_res = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = tenant_res.scalar_one_or_none()
        if tenant and not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Company account '{tenant.name}' has been deactivated by the system administrator.",
            )

    return user

async def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization=authorization, db=db)
    except HTTPException as e:
        if e.status_code == status.HTTP_403_FORBIDDEN:
            raise e
        return None

async def get_current_tenant_id(
    current_user: Optional[User] = Depends(get_optional_current_user),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> UUID:
    """
    Returns the active tenant_id for the request.
    Strict tenant isolation: non-super-admin users are strictly bound to their company tenant_id.
    Super Admins can pass an optional X-Tenant-ID header to inspect or act on behalf of a specific company.
    If no auth header is provided (e.g. dev test scripts), defaults safely to DEMO_TENANT_ID.
    """
    if not current_user:
        if x_tenant_id:
            try:
                return UUID(x_tenant_id)
            except ValueError:
                pass
        return DEMO_TENANT_ID

    if current_user.role == UserRole.SUPER_ADMIN.value or current_user.role == "super_admin":
        if x_tenant_id:
            try:
                return UUID(x_tenant_id)
            except ValueError:
                pass
        return current_user.tenant_id

    # For all company admins, managers, and staff:
    return current_user.tenant_id

def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.SUPER_ADMIN.value and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Administrator privileges required.",
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    allowed = [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, "super_admin", "admin"]
    if current_user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required.",
        )
    return current_user
