import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
    ListFlowable,
    ListItem,
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total page count and add running header/footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Skip header and footer on cover page
        if self._pageNumber > 1:
            # Running Header
            self.drawString(54, 752, "INVENZA ENTERPRISE IMS — ARCHITECTURE & USER MANUAL")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

            # Running Footer
            self.line(54, 45, 558, 45)
            self.drawString(54, 32, "Confidential — Invenza Cloud Platform 2026")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(558, 32, page_text)

        self.restoreState()

def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Palettes
    primary_color = colors.HexColor("#1e1b4b")  # Deep Navy Indigo
    accent_color = colors.HexColor("#4f46e5")   # Vibrant Indigo
    emerald_color = colors.HexColor("#059669")  # Emerald
    dark_text = colors.HexColor("#0f172a")      # Slate 900
    sub_text = colors.HexColor("#475569")       # Slate 600
    card_bg = colors.HexColor("#f8fafc")        # Slate 50
    border_color = colors.HexColor("#cbd5e1")   # Slate 300

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=accent_color,
        spaceAfter=15,
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=accent_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_text,
        spaceAfter=6,
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold',
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=dark_text,
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=primary_color,
    )

    story = []

    # ==================== COVER / HEADER BANNER ====================
    story.append(Paragraph("INVENZA PLATFORM MANUAL", subtitle_style))
    story.append(Paragraph("Next-Gen Multi-Tenant SaaS Inventory Management System", title_style))
    story.append(Paragraph("A Comprehensive Architectural Overview, Component Manual, and Plain-English Guide to Enterprise Inventory Control", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=accent_color, spaceBefore=4, spaceAfter=14))

    # Meta table (Author, Date, Version)
    meta_data = [
        [
            Paragraph("<b>Target Audience:</b> Business Analysts, Engineers & Non-Technical Teams", table_cell_style),
            Paragraph("<b>Version:</b> 2.4 Enterprise Release", table_cell_style),
            Paragraph("<b>Status:</b> Production Ready", table_cell_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[240, 130, 134])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_bg),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # ==================== CHAPTER 1: WHAT IS AN IMS? ====================
    story.append(Paragraph("1. What is an Inventory Management System (IMS)?", h1_style))
    story.append(Paragraph(
        "Imagine you run a retail store or a factory. You have products arriving from suppliers, items sitting on warehouse shelves, orders being packed for customers, and occasional damaged goods. If you try managing this with pen and paper or standard Excel spreadsheets, chaos is inevitable: numbers get overwritten, nobody knows who changed a quantity, goods sell out without warning, and capital gets locked up in unsold stock.",
        body_style
    ))
    story.append(Paragraph(
        "An <b>Inventory Management System (IMS)</b> serves as the <b>central digital nervous system</b> for all physical physical goods moving into, through, and out of an enterprise. It guarantees three fundamental truths: <i>What do we own? Where is it located right now? What is its financial value?</i>",
        body_style
    ))

    # Callout Box: Why Spreadsheets Fail
    callout_data = [[
        Paragraph(
            "<b>Why Traditional Spreadsheets Fail:</b><br/>"
            "• <b>Destructive Overwrites:</b> When someone edits stock from 50 to 45 in Excel, the historical record of <i>why</i> it changed is lost forever.<br/>"
            "• <b>Ghost Inventory:</b> Items shown in stock on paper that cannot be found on the physical shelf.<br/>"
            "• <b>No Real-Time Auditing:</b> Zero accountability for shrinkage, theft, or miscounts.<br/>"
            "• <b>Multi-Location Blindness:</b> Spreadsheets cannot reliably coordinate live transfers between 10 different regional warehouses.",
            callout_style
        )
    ]]
    callout_table = Table(callout_data, colWidths=[504])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eef2ff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#818cf8")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 12))

    # ==================== CHAPTER 2: CORE INVENTORY CONCEPTS ====================
    story.append(Paragraph("2. Core Concepts Explained Simply", h1_style))

    story.append(Paragraph("<b>A. SKU (Stock Keeping Unit)</b>", h2_style))
    story.append(Paragraph(
        "A SKU is the unique alphanumeric fingerprint assigned to each distinct product variant. For example, <code>SKU-KB-101-BLK</code> specifically represents a 'Black Wireless Keyboard'. Every unit of measure, sell price, barcode, and reorder threshold attaches directly to this SKU identifier.",
        body_style
    ))

    story.append(Paragraph("<b>B. The Immutable Stock Movement Ledger (Double-Entry for Inventory)</b>", h2_style))
    story.append(Paragraph(
        "Traditional naive inventory software simply executes <code>UPDATE products SET stock = stock - 10</code>. Invenza rejects this paradigm. Instead, Invenza implements a financial-grade <b>Immutable Stock Ledger</b>. You cannot simply overwrite stock. Every addition or subtraction is an unalterable transaction record with timestamp, operator, source, destination, unit cost, and reason. Current stock is dynamically computed as the sum of all historical transactions, ensuring 100% audit integrity.",
        body_style
    ))

    story.append(Paragraph("<b>C. Multi-Tenancy (Strict Organization Isolation)</b>", h2_style))
    story.append(Paragraph(
        "Invenza is built as a true multi-tenant SaaS application. Imagine a modern luxury skyscraper: each tenant company (e.g. <i>Hapkonic</i> or <i>Nova BioPharma</i>) has its own locked private penthouse with dedicated keys. Both companies share the building infrastructure, but they can never peek into each other's rooms. All database records, warehouses, team users, and SKUs are scoped by a cryptographic <code>tenant_id</code>.",
        body_style
    ))

    story.append(Paragraph("<b>D. Purchase Orders (Inbound) vs. Sales Orders (Outbound)</b>", h2_style))
    story.append(Paragraph(
        "• <b>Purchase Order (PO):</b> A contract sent to a vendor/supplier to buy goods. When the truck arrives at the warehouse loading dock, staff inspect and 'Receive' the goods, which automatically logs positive (+IN) ledger transactions.<br/>"
        "• <b>Sales Order (SO):</b> A demand order placed by a customer. When the warehouse team picks and packs the goods, 'Fulfilling' the SO generates negative (-OUT) ledger entries, preventing stock-outs.",
        body_style
    ))

    story.append(Paragraph("<b>E. Stock Transfers & Auditing Adjustments</b>", h2_style))
    story.append(Paragraph(
        "• <b>Transfers:</b> Move items between physical warehouses (e.g. Central Depot -> Retail Store) while tracking in-transit status so items never vanish during transport.<br/>"
        "• <b>Adjustments:</b> Reconcile real-world discrepancies (damaged cartons, shrinkage, or physical count audits) with mandatory reason codes.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ==================== CHAPTER 3: COMPONENT-BY-COMPONENT GUIDE ====================
    story.append(Paragraph("3. Invenza Component Manual: What Every Screen Does", h1_style))

    components_data = [
        [
            Paragraph("Component / Page", table_header_style),
            Paragraph("Primary Purpose", table_header_style),
            Paragraph("Key Operational Features", table_header_style),
        ],
        [
            Paragraph("<b>Executive Dashboard</b>", table_cell_bold),
            Paragraph("High-level operational cockpit for business managers.", table_cell_style),
            Paragraph("Total inventory valuation, low stock warnings, open POs/SOs, real-time stock flow chart, quick navigation.", table_cell_style),
        ],
        [
            Paragraph("<b>Product & SKU Catalog</b>", table_cell_bold),
            Paragraph("Master repository of all items offered by the organization.", table_cell_style),
            Paragraph("Dynamic JSONB attributes, barcode label printing, instant CSV Template download, CSV batch import modal.", table_cell_style),
        ],
        [
            Paragraph("<b>Stock Movement Ledger</b>", table_cell_bold),
            Paragraph("Audit-proof history of every physical goods transaction.", table_cell_style),
            Paragraph("Filterable by warehouse location and movement type (IN, OUT, ADJUST, TRANSFER), running balance calculation.", table_cell_style),
        ],
        [
            Paragraph("<b>Purchase Orders (Procurement)</b>", table_cell_bold),
            Paragraph("Manages inbound supplier logistics and purchasing.", table_cell_style),
            Paragraph("Multi-item PO generator, draft/pending/received lifecycle, goods inspection receiving modal with ledger sync.", table_cell_style),
        ],
        [
            Paragraph("<b>Sales Orders (Fulfillment)</b>", table_cell_bold),
            Paragraph("Handles customer demand, picking, and fulfillment.", table_cell_style),
            Paragraph("Live stock availability validation, automatic stock deduction upon fulfillment, order status tracking.", table_cell_style),
        ],
        [
            Paragraph("<b>Stock Transfers</b>", table_cell_bold),
            Paragraph("Inter-facility logistics coordination.", table_cell_style),
            Paragraph("Move inventory between locations, track in-transit goods, prevent double-counting across facilities.", table_cell_style),
        ],
        [
            Paragraph("<b>Adjustments & Audits</b>", table_cell_bold),
            Paragraph("Physical count discrepancy reconciliation.", table_cell_style),
            Paragraph("Mandatory audit reason codes (Damage, Loss, Miscount, Audit Take), compliance justification notes.", table_cell_style),
        ],
        [
            Paragraph("<b>Multi-Warehouse Hub</b>", table_cell_bold),
            Paragraph("Physical facilities and distribution center management.", table_cell_style),
            Paragraph("Warehouse address registry, maximum volumetric capacity tracking, per-facility utilization rates.", table_cell_style),
        ],
        [
            Paragraph("<b>Valuation & Reports</b>", table_cell_bold),
            Paragraph("Financial and accounting insights into stock assets.", table_cell_style),
            Paragraph("Real-time comparative valuation engine supporting both FIFO (First-In, First-Out) and Weighted Average Costing.", table_cell_style),
        ],
        [
            Paragraph("<b>Super Admin Console</b>", table_cell_bold),
            Paragraph("Multi-tenant enterprise SaaS management engine.", table_cell_style),
            Paragraph("Provision new tenant companies, select enabled industry modules, trigger live SMTP welcome emails with credentials.", table_cell_style),
        ],
        [
            Paragraph("<b>Invenza AI Copilot</b>", table_cell_bold),
            Paragraph("Natural language conversational inventory analyst.", table_cell_style),
            Paragraph("Answers live catalog queries, highlights low stock SKUs, recommends reorder purchase quantities.", table_cell_style),
        ],
    ]

    comp_table = Table(components_data, colWidths=[115, 140, 249])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, card_bg]),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 14))

    # ==================== CHAPTER 4: TECHNOLOGY STACK ====================
    story.append(Paragraph("4. Technical Architecture & Technology Stack", h1_style))
    story.append(Paragraph(
        "Invenza is architected with modern, enterprise-grade cloud technologies built for high availability, sub-50ms API response times, and bulletproof horizontal scaling.",
        body_style
    ))

    tech_data = [
        [
            Paragraph("Architectural Tier", table_header_style),
            Paragraph("Technologies Used", table_header_style),
            Paragraph("Role & Why It Was Chosen", table_header_style),
        ],
        [
            Paragraph("<b>Frontend Client</b>", table_cell_bold),
            Paragraph("React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons", table_cell_style),
            Paragraph("Lightning-fast SPA compilation, strict typing, responsive glassmorphic dark/light interface, zero UI lag.", table_cell_style),
        ],
        [
            Paragraph("<b>Backend API Engine</b>", table_cell_bold),
            Paragraph("Python 3.12, FastAPI, Pydantic v2, Uvicorn ASGI", table_cell_style),
            Paragraph("Asynchronous I/O capable of thousands of concurrent requests, automatic OpenAPI documentation, schema validation.", table_cell_style),
        ],
        [
            Paragraph("<b>Primary Database</b>", table_cell_bold),
            Paragraph("PostgreSQL 16, SQLAlchemy 2.0 (Async), Alembic", table_cell_style),
            Paragraph("ACID compliance, JSONB dynamic document storage for custom industry schemas, foreign-key multi-tenant isolation.", table_cell_style),
        ],
        [
            Paragraph("<b>Object Storage</b>", table_cell_bold),
            Paragraph("MinIO (Distributed S3-Compatible Storage)", table_cell_style),
            Paragraph("Stores immutable audit documents, quality certificates, supplier invoices, and catalog export archives.", table_cell_style),
        ],
        [
            Paragraph("<b>Cache & Fast Broker</b>", table_cell_bold),
            Paragraph("Redis 7 (In-Memory Key-Value Store)", table_cell_style),
            Paragraph("Sub-millisecond query caching, user session state, and background task synchronization.", table_cell_style),
        ],
        [
            Paragraph("<b>Vector AI Store</b>", table_cell_bold),
            Paragraph("Qdrant Vector Database", table_cell_style),
            Paragraph("Powers semantic search and retrieval-augmented generation (RAG) for the Invenza AI Copilot.", table_cell_style),
        ],
        [
            Paragraph("<b>Notification Engine</b>", table_cell_bold),
            Paragraph("SMTP Live Transport (Gmail / TLS Port 587)", table_cell_style),
            Paragraph("Automated dispatch of HTML credential emails to provisioned company admins and invited team members.", table_cell_style),
        ],
        [
            Paragraph("<b>Containerization</b>", table_cell_bold),
            Paragraph("Docker, Docker Compose", table_cell_style),
            Paragraph("One-click reproducible local deployment of PostgreSQL, MinIO, Redis, Qdrant, and app services.", table_cell_style),
        ],
    ]

    tech_table = Table(tech_data, colWidths=[115, 140, 249])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, card_bg]),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 14))

    # ==================== CHAPTER 5: TYPICAL WORKFLOW ====================
    story.append(Paragraph("5. Step-by-Step Operational Lifecycle in Invenza", h1_style))

    workflow_steps = [
        "<b>1. Tenant Provisioning:</b> The Super Administrator creates a company account (e.g. <i>Apex Logistics</i>). Invenza generates isolated credentials and dispatches an automated HTML welcome email via SMTP.",
        "<b>2. Catalog Setup:</b> The Company Admin downloads the standardized <b>CSV Template</b> with required headers (<code>sku</code>, <code>name</code>) and uploads their product roster via the <b>Import CSV</b> modal.",
        "<b>3. Procuring Stock:</b> A Purchase Order is drafted for 100 units of a SKU from a vendor. When goods arrive, the warehouse operator confirms the quantities in the <i>Receive Goods</i> dialog. The stock ledger immediately credits +100 units.",
        "<b>4. Selling & Fulfilling:</b> A customer orders 20 units. A Sales Order is created and verified against live stock. Fulfilling the order debits -20 units in the ledger and prints packing slips.",
        "<b>5. Real-Time Valuation:</b> The finance team opens the <i>Reports</i> tab to inspect current inventory asset value calculated across FIFO batches and weighted average cost.",
    ]

    for step in workflow_steps:
        story.append(Paragraph(f"• {step}", body_style))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceBefore=4, spaceAfter=10))
    story.append(Paragraph("<b>End of Document</b> — Generated by Invenza Platform Documentation Engine &copy; 2026", callout_style))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF Generation SUCCESS]: Created '{filename}'")

if __name__ == "__main__":
    output_path = Path(__file__).resolve().parent / "Invenza_Platform_Architecture_and_User_Guide.pdf"
    build_pdf(str(output_path))
