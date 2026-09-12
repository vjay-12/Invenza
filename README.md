# Invenza — Modern General-Purpose Inventory Management SaaS

**Invenza** is an enterprise-grade, general-purpose (industry-agnostic) inventory management SaaS engineered to solve the chronic pain points of legacy ERPs and modern tools.

---

## 🚀 Key Architectural Innovations

1. **Immutable Movement Ledger**: Stock levels are never stored as mutable integer fields that can be silently edited or drifted. Current stock is deterministically aggregated from signed movement events (`IN`, `OUT`, `ADJUST`, `TRANSFER`).
2. **Dynamic JSONB Custom Fields Engine**: Solves the #1 complaint across competitor tools ("Limited Customization"). Admins can dynamically define bespoke attributes (Batch #, Expiry Date, Warehouse Zone, Dimensions) without database migrations.
3. **Goods Received Note (GRN) & Fulfillment Pipelines**:
   - **PO → GRN**: Receiving goods automatically writes cryptographic `IN` entries to the target warehouse ledger with unit cost stamps.
   - **SO → Fulfillment**: Fulfilling customer orders checks real-time available stock in the dispatch location and writes `OUT` ledger entries.
4. **Inter-Warehouse Paired Transfers**: Multi-location support from day one. Dispatches create paired balancing entries between source and destination hubs.
5. **Mandatory Reason Codes**: Adjustments require strict categorizations (`damage`, `loss`, `miscount`, `return`, `audit`) and written justification notes for complete audit compliance.
6. **Dual Costing Models**: Instant side-by-side comparison between **FIFO (First-In, First-Out)** and **Weighted Average Costing**.
7. **Dual-Engine Invenza AI Copilot**:
   - `query_inventory_db`: Read-only, tenant-isolated Text-to-SQL engine with strict `SELECT`-only validation and AST safety guardrails.
   - `search_docs`: pgvector semantic RAG retriever over inventory SOPs and valuation rules.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + Vite + Tailwind CSS + Lucide Icons + Recharts |
| **Backend** | Python 3.11+ / 3.14 + FastAPI + SQLAlchemy 2.0 (Async) + Alembic |
| **Database** | PostgreSQL 16 + `pgvector` extension |
| **Storage & Jobs** | MinIO (S3-compatible) + FastAPI BackgroundTasks |
| **Authentication** | JWT Bearer Tokens with tenant scoping & RBAC (`Admin`, `Staff`, `Viewer`) |
| **Containerization** | Docker + Docker Compose |

> **Multi-region tax:** GST (India) / VAT (EU) / Sales Tax (US) with INR/EUR/USD
> billing is configured via the `tax_reference` table — see
> [docs/TAX_REFERENCE.md](docs/TAX_REFERENCE.md) for rates, re-verification
> requirements, and how to add countries/states without code changes.

---

## 🏃 Quick Start (Local Development)

### 1. Frontend Development Server

The frontend is client-side rendered with a mock dataset and full interactive state:

```bash
cd frontend
npm install
npm run dev
```

Visit **`http://localhost:5173`** in your browser.

- **Keyboard Shortcut**: Press `Ctrl + K` (or `Cmd + K`) anywhere to open the Quick Command Palette.
- **AI Assistant**: Click the glowing **Invenza Copilot** badge at the bottom-right or in the navbar.
- **Theme Switcher**: Click the Sun/Moon toggle in the top-right navbar.
- **Currency Switcher**: Toggle between `USD ($)`, `EUR (€)`, `INR (₹)`, and `GBP (£)` instantly.

### 2. Backend API Server

```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger documentation is available at **`http://localhost:8000/docs`**.

### 3. Full Stack with Docker Compose

To start PostgreSQL with `pgvector`, MinIO, the FastAPI backend, and the frontend bundle in Docker:

```bash
docker-compose up -d --build
```

- **Frontend App**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000/docs`
- **MinIO Console**: `http://localhost:9001` (User: `invenza_minio_admin`, Pass: `invenza_minio_secret_password`)
- **PostgreSQL**: `localhost:5432` (`invenza_db`)

---

## 📁 Repository Structure

```
Invenza/
├── docker-compose.yml              # PostgreSQL (with pgvector), MinIO, Backend, Frontend
├── README.md                       # Documentation & Quickstart
│
├── frontend/                       # React 19 + Vite + Tailwind CSS
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                  # Main tab router and provider wrapper
│       ├── index.css                # Google Fonts, glassmorphic styling, scrollbars
│       ├── types/
│       │   └── inventory.ts         # TypeScript interfaces
│       ├── data/
│       │   └── platformConstants.ts # Industry & platform module definitions
│       ├── context/
│       │   ├── InventoryContext.tsx # Central state manager & ledger aggregator
│       │   └── ThemeContext.tsx     # Dark / Light theme manager
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Navbar.tsx       # Search, currency, warehouse switcher, theme toggle
│       │   │   ├── Sidebar.tsx      # Navigation links with live badge counts
│       │   │   └── QuickSearchModal.tsx # Command palette (Ctrl+K)
│       │   ├── common/
│       │   │   ├── StatCard.tsx     # Metric cards with gradients and trends
│       │   │   ├── Badge.tsx        # Movement pills (IN/OUT/TRANSFER/ADJUST)
│       │   │   ├── Modal.tsx        # Accessible dialog with blur backdrop
│       │   │   └── BarcodeLabelModal.tsx # Barcode sheet generator with Code128 pattern
│       │   └── chat/
│       │       └── InvenzaChatbot.tsx # Floating AI Copilot (Text-to-SQL + RAG)
│       └── pages/
│           ├── Dashboard.tsx        # Operations overview, Recharts flow, low stock banner
│           ├── Products.tsx         # SKU master, variants, custom fields, bulk edit
│           ├── Ledger.tsx           # Immutable stock movement stream & running balances
│           ├── PurchaseOrders.tsx   # PO creator & Goods Received Note (GRN) workflow
│           ├── SalesOrders.tsx      # SO creator & warehouse fulfillment workflow
│           ├── Transfers.tsx        # Inter-warehouse paired movement transfer pipeline
│           ├── Adjustments.tsx      # Stock reconciliation with mandatory reason codes
│           ├── Warehouses.tsx       # Multi-location cards & capacity utilization
│           ├── Reports.tsx          # FIFO vs Weighted Average Costing comparison
│           └── Settings.tsx         # JSONB custom fields schema builder & webhooks
│
└── backend/                        # Python FastAPI Async Architecture
    ├── requirements.txt
    ├── Dockerfile
    └── app/
        ├── main.py                  # FastAPI app & CORS configuration
        ├── core/
        │   ├── config.py            # Environment & app settings
        │   ├── database.py          # Async SQLAlchemy engine & sessionmaker
        │   └── security.py          # Password hashing & tenant-scoped JWT auth
        ├── models/                  # Declarative SQLAlchemy models
        │   ├── tenant.py            # Tenant isolation
        │   ├── user.py              # RBAC roles
        │   ├── product.py           # Product master with JSONB custom fields
        │   ├── location.py          # Multi-warehouse locations
        │   ├── ledger.py            # Immutable StockMovement table
        │   ├── order.py             # PurchaseOrder & SalesOrder headers and items
        │   ├── transfer.py          # StockTransfer paired records
        │   ├── adjustment.py        # StockAdjustment with reason codes
        │   ├── webhook.py           # Outbound webhook configurations
        │   └── documentation.py     # Help docs chunks with pgvector embeddings
        ├── schemas/                 # Pydantic v2 schemas
        │   ├── product.py
        │   ├── ledger.py
        │   └── ai.py
        └── services/
            └── ai_orchestrator.py   # Dual-tool orchestrator (Text-to-SQL + pgvector RAG)
```
