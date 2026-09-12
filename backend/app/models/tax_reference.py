import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Numeric, DateTime, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class TaxReference(Base):
    """
    Regional tax reference table keyed by Country + State (never by currency).

    Tax lookups are ALWAYS Country + State -> this table. The `currency` column is
    informational/display-only and must never drive tax rate or tax type decisions.

    Rows are seed data (see app/db/init_db.py::seed_tax_reference_table). Rates must be
    periodically re-verified against official sources (EU TEDB / state Depts. of Revenue)
    and updated in place via a data update — adding a new region is a row insert, not a
    code change.
    """
    __tablename__ = "tax_reference"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(2), nullable=False, index=True)   # ISO 3166-1 alpha-2 (IN, DE, US...)
    state_code = Column(String(10), nullable=True)                 # India: GST code ('29'); US: 2-letter ('CA'); NULL for EU
    tax_type = Column(String(20), nullable=False)                  # GST / VAT / SALES_TAX
    tax_rate = Column(Numeric(5, 2), nullable=False)               # applicable standard rate (%)
    currency = Column(String(3), nullable=False)                   # display currency for the region (informational only)
    is_zero_rate = Column(Boolean, default=False, nullable=False)  # e.g. Delaware, Oregon (0% still rendered, not omitted)
    sourcing_rule = Column(String(20), nullable=True)              # origin / destination (US states; NULL elsewhere)
    last_verified_date = Column(Date, nullable=False, default=date.today)
    source_reference = Column(String(500), nullable=False)         # authoritative source used for the rate
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Uniqueness of (country_code, state_code) is enforced by the expression index
    # uq_tax_reference_country_state created in init_db.py — COALESCE(state_code, '')
    # is required because PostgreSQL treats NULLs as distinct under plain unique constraints.
