import uuid
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.api.deps import require_super_admin
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog
from app.core.security import get_password_hash
from app.services.email_service import EmailService
from app.models.security_request import SecurityApprovalRequest

router = APIRouter()

MASTER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

def get_default_permissions_for_role(role: str) -> List[str]:
    r = (role or "").lower()
    if r in ["admin", UserRole.ADMIN.value]:
        return [
            "inventory:read", "inventory:write", "orders:manage",
            "team:manage", "reports:view", "settings:manage"
        ]
    elif r in ["manager", UserRole.MANAGER.value]:
        return ["inventory:read", "inventory:write", "orders:manage", "reports:view"]
    elif r in ["staff", UserRole.STAFF.value]:
        return ["inventory:read", "inventory:write", "orders:manage"]
    elif r in ["viewer", UserRole.VIEWER.value]:
        return ["inventory:read", "reports:view"]
    return []

class CreateOrgUserRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: str = "staff"
    permissions: Optional[List[str]] = None
    send_email: Optional[bool] = False

class RoleUpdateRequest(BaseModel):
    role: str  # 'admin', 'manager', 'staff', 'viewer'
    permissions: List[str]
    force_last_admin: Optional[bool] = False

class UserStatusRequest(BaseModel):
    is_active: bool

class RoleOrgSummary(BaseModel):
    id: UUID
    name: str
    company_code: Optional[str] = None
    unique_code: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    member_count: int = 0
    admin_count: int = 0
    admin_email: Optional[str] = None

class RoleUserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    full_name: str
    email: str
    role: str
    permissions: List[str]
    is_active: bool
    created_at: datetime

@router.get("/organizations", response_model=List[RoleOrgSummary])
async def list_role_organizations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: Retrieve all active organizations with team metadata for Role Management org picker.
    """
    tenants_res = await db.execute(
        select(Tenant).where(and_(Tenant.is_active == True, Tenant.id != MASTER_TENANT_ID)).order_by(Tenant.name.asc())
    )
    tenants = tenants_res.scalars().all()

    result: List[RoleOrgSummary] = []
    for t in tenants:
        users_res = await db.execute(select(User).where(User.tenant_id == t.id))
        users = users_res.scalars().all()
        admins = [u for u in users if u.role in ["admin", UserRole.ADMIN.value] and u.is_active]

        result.append(RoleOrgSummary(
            id=t.id,
            name=t.name,
            company_code=t.company_code or t.unique_code,
            unique_code=t.unique_code or t.company_code,
            industry=t.industry or "General Merchandise",
            location=t.location or "Headquarters",
            is_active=t.is_active,
            member_count=len(users),
            admin_count=len(admins),
            admin_email=admins[0].email if admins else None,
        ))

    return result

@router.get("/organizations/{tenant_id}/team", response_model=List[RoleUserResponse])
async def get_organization_team(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """
    Super Admin: Retrieve all operators/users belonging to a specific organization.
    Ensures complete granted permissions are accurately returned for every role tier.
    """
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")

    users_res = await db.execute(select(User).where(User.tenant_id == tenant_id).order_by(User.created_at.asc()))
    users = users_res.scalars().all()

    return [
        RoleUserResponse(
            id=u.id,
            tenant_id=u.tenant_id,
            full_name=u.full_name,
            email=u.email,
            role=u.role,
            permissions=(u.permissions if u.permissions and len(u.permissions) > 0 else get_default_permissions_for_role(u.role)),
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]

@router.post("/organizations/{tenant_id}/users", response_model=RoleUserResponse, status_code=status.HTTP_201_CREATED)
async def create_organization_user(
    tenant_id: UUID,
    user_in: CreateOrgUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Create and enroll a new operator/member into any tenant organization.
    """
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")

    email_clean = user_in.email.strip().lower()
    existing = await db.execute(select(User).where(User.email == email_clean))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email_clean}' already exists.",
        )

    role_clean = user_in.role.strip().lower()
    perms = user_in.permissions
    if not perms or len(perms) == 0:
        perms = get_default_permissions_for_role(role_clean)

    new_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email_clean,
        full_name=user_in.full_name.strip(),
        hashed_password=get_password_hash(user_in.password),
        role=role_clean,
        permissions=perms,
        is_active=True,
    )
    db.add(new_user)

    # Audit log
    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        action_type="member_create",
        target_type="user",
        target_id=str(new_user.id),
        description=f"Enrolled operator {new_user.full_name} ({new_user.email}) as {role_clean.capitalize()} in {tenant.name}",
        after_values={
            "full_name": new_user.full_name,
            "email": new_user.email,
            "role": new_user.role,
            "permissions": new_user.permissions,
        },
    ))

    await db.commit()
    await db.refresh(new_user)

    if user_in.send_email:
        try:
            await EmailService.send_staff_user_credentials(
                company_name=tenant.name,
                user_name=new_user.full_name,
                user_email=new_user.email,
                temporary_password=user_in.password,
                role=new_user.role,
                permissions=new_user.permissions,
            )
        except Exception:
            pass

    return RoleUserResponse(
        id=new_user.id,
        tenant_id=new_user.tenant_id,
        full_name=new_user.full_name,
        email=new_user.email,
        role=new_user.role,
        permissions=new_user.permissions or [],
        is_active=new_user.is_active,
        created_at=new_user.created_at,
    )

@router.put("/users/{user_id}/role")
async def update_user_role_and_permissions(
    user_id: UUID,
    req: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Update role tier and toggle granular permissions for a tenant member.
    Enforces strict sole-admin demotion blocking.
    """
    user_res = await db.execute(select(User).where(User.id == user_id))
    target_user = user_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == target_user.tenant_id))
    tenant = tenant_res.scalar_one_or_none()

    # Guardrail: Check if changing role away from admin when user is the last active admin
    is_currently_admin = target_user.role in ["admin", UserRole.ADMIN.value]
    will_be_admin = req.role in ["admin", UserRole.ADMIN.value]

    if is_currently_admin and not will_be_admin:
        active_admins_res = await db.execute(
            select(User).where(and_(
                User.tenant_id == target_user.tenant_id,
                User.role.in_(["admin", UserRole.ADMIN.value]),
                User.is_active == True,
                User.id != target_user.id,
            ))
        )
        other_admins = active_admins_res.scalars().all()
        if len(other_admins) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assign another user as Admin first, then update this user to {req.role.capitalize()}."
            )

    before_vals = {
        "role": target_user.role,
        "permissions": target_user.permissions,
    }

    target_user.role = req.role
    target_user.permissions = req.permissions

    after_vals = {
        "role": target_user.role,
        "permissions": target_user.permissions,
    }

    # Audit Log
    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=target_user.tenant_id,
        tenant_name=tenant.name if tenant else None,
        action_type="role_change",
        target_type="user",
        target_id=str(target_user.id),
        description=f"Updated role for {target_user.full_name} ({target_user.email}) to {req.role.capitalize()} with {len(req.permissions)} permissions",
        before_values=before_vals,
        after_values=after_vals,
    ))

    await db.commit()
    await db.refresh(target_user)

    # Dispatch official role & access change notification to user
    try:
        await EmailService.send_role_change_notification(
            user_email=target_user.email,
            user_name=target_user.full_name or "Team Member",
            company_name=tenant.name if tenant else "Invenza Enterprise",
            previous_role=before_vals["role"],
            new_role=target_user.role,
            permissions_count=len(target_user.permissions or []),
            admin_name=admin.full_name or "Super Admin",
        )
    except Exception as e:
        print(f"[Role Change Email Warning]: {e}")

    return {
        "success": True,
        "message": f"Updated {target_user.full_name}'s role to {req.role.capitalize()}",
        "user": {
            "id": target_user.id,
            "full_name": target_user.full_name,
            "role": target_user.role,
            "permissions": target_user.permissions,
        }
    }

@router.patch("/users/{user_id}/status")
async def toggle_user_status(
    user_id: UUID,
    req: UserStatusRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Super Admin: Suspend or reactivate an organization member.
    """
    user_res = await db.execute(select(User).where(User.id == user_id))
    target_user = user_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == target_user.tenant_id))
    tenant = tenant_res.scalar_one_or_none()

    before_vals = {"is_active": target_user.is_active}
    target_user.is_active = req.is_active
    after_vals = {"is_active": target_user.is_active}

    action_label = "member_reactivate" if req.is_active else "member_suspend"
    desc_label = "Reactivated" if req.is_active else "Suspended"

    # Audit Log
    db.add(AuditLog(
        actor_id=admin.id,
        actor_name=admin.full_name or "Super Admin",
        actor_email=admin.email,
        tenant_id=target_user.tenant_id,
        tenant_name=tenant.name if tenant else None,
        action_type=action_label,
        target_type="user",
        target_id=str(target_user.id),
        description=f"{desc_label} account for {target_user.full_name} ({target_user.email}) in {tenant.name if tenant else 'Org'}",
        before_values=before_vals,
        after_values=after_vals,
    ))

    await db.commit()
    await db.refresh(target_user)

    return {
        "success": True,
        "message": f"User account has been {desc_label.lower()}",
        "is_active": target_user.is_active,
    }
