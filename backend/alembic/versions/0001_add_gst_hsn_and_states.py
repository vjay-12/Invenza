"""add_gst_hsn_and_states

Revision ID: 0001_add_gst_hsn_and_states
Revises: 
Create Date: 2026-09-07 12:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_add_gst_hsn_and_states'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Product HSN and GST rate classification columns
    conn = op.get_bind()
    
    # Products table
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS hsn_code VARCHAR(20) NOT NULL DEFAULT '8471';")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS gst_rate NUMERIC(5, 2) NOT NULL DEFAULT 18.00;")

    # Sales Orders table - customer bill-to & ship-to state data
    op.execute("ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS billing_state VARCHAR(100);")
    op.execute("ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS billing_state_code VARCHAR(2);")
    op.execute("ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS shipping_state VARCHAR(100);")
    op.execute("ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS shipping_state_code VARCHAR(2);")

    # Customers table - bill-to & ship-to state data
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_state VARCHAR(100);")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_state_code VARCHAR(2);")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS shipping_state VARCHAR(100);")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS shipping_state_code VARCHAR(2);")


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS hsn_code;")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS gst_rate;")
    op.execute("ALTER TABLE sales_orders DROP COLUMN IF EXISTS billing_state;")
    op.execute("ALTER TABLE sales_orders DROP COLUMN IF EXISTS billing_state_code;")
    op.execute("ALTER TABLE sales_orders DROP COLUMN IF EXISTS shipping_state;")
    op.execute("ALTER TABLE sales_orders DROP COLUMN IF EXISTS shipping_state_code;")
    op.execute("ALTER TABLE customers DROP COLUMN IF EXISTS billing_state;")
    op.execute("ALTER TABLE customers DROP COLUMN IF EXISTS billing_state_code;")
    op.execute("ALTER TABLE customers DROP COLUMN IF EXISTS shipping_state;")
    op.execute("ALTER TABLE customers DROP COLUMN IF EXISTS shipping_state_code;")
