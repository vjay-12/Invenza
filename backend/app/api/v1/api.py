from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    products,
    ledger,
    orders,
    locations,
    transfers,
    adjustments,
    reports,
    storage,
    superadmin,
    company_users,
    invoices,
    danger_zone,
    leads,
    profile,
    billing,
    safeguards,
    role_management,
)
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.ai_orchestrator import AIOrchestrator

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(profile.router, prefix="/profile", tags=["User & Organization Profile"])
api_router.include_router(leads.router, prefix="/leads", tags=["Prospective Leads & Quotations"])
api_router.include_router(danger_zone.router, prefix="/danger-zone", tags=["Danger Zone & Security Safeguards"])
api_router.include_router(safeguards.router, prefix="/safeguards", tags=["Security Safeguards & Approvals"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing & Subscriptions"])
api_router.include_router(role_management.router, prefix="/role-management", tags=["Platform Role Management"])
api_router.include_router(superadmin.router, prefix="/superadmin", tags=["Super Admin Multi-Tenant Console"])
api_router.include_router(company_users.router, prefix="/company/users", tags=["Company Team & RBAC Management"])
api_router.include_router(products.router, prefix="/products", tags=["Products & SKUs"])
api_router.include_router(ledger.router, prefix="/ledger", tags=["Movement Ledger"])
api_router.include_router(orders.router, prefix="/orders", tags=["Purchase & Sales Orders"])
api_router.include_router(locations.router, prefix="/locations", tags=["Warehouses & Locations"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["Stock Transfers"])
api_router.include_router(adjustments.router, prefix="/adjustments", tags=["Manual Adjustments"])
api_router.include_router(reports.router, prefix="/reports", tags=["Valuation & Reports"])
api_router.include_router(storage.router, prefix="/storage", tags=["MinIO Object Storage & Attachments"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["GST Invoicing & Taxation"])

@api_router.post("/assistant/chat", response_model=ChatResponse, tags=["Invenza Copilot AI"])
async def chat_with_copilot(request: ChatRequest):
    """
    Unified Invenza Copilot endpoint orchestrating Text-to-SQL (query_inventory_db)
    and pgvector RAG (search_docs).
    """
    response = await AIOrchestrator.process_chat(request)
    return response
