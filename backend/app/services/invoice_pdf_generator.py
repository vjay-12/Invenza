"""
ReportLab 5.0+ GST-Compliant Vector Tax Invoice PDF Generator for Invenza.
Generates print-resolution, beautifully formatted invoices with custom headers,
Bill To / Ship To grids, dynamic CGST/SGST vs IGST tables, bank details,
authorized signature, and VOID watermarks.
"""

import io
import os
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Invenza Brand Colors
TEAL_PRIMARY = colors.HexColor("#0E7490")     # Petrol Teal 700
TEAL_DARK = colors.HexColor("#155E75")        # Petrol Teal 800
TEAL_LIGHT = colors.HexColor("#F0FDFA")       # Petrol Teal 50
SLATE_DARK = colors.HexColor("#0F172A")       # Slate 900
SLATE_MUTED = colors.HexColor("#475569")      # Slate 600
SLATE_LIGHT = colors.HexColor("#F8FAFC")      # Slate 50
BORDER_COLOR = colors.HexColor("#CBD5E1")     # Slate 300

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for total page count, header bar, and VOID watermark.
    """
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []
        self.is_void = False

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()

        # VOID Watermark if invoice is voided
        if getattr(self, "is_void", False):
            self.setFont("Helvetica-Bold", 72)
            self.setFillColor(colors.HexColor("#DC2626"), alpha=0.18)
            self.translate(A4[0] / 2.0, A4[1] / 2.0)
            self.rotate(45)
            self.drawCentredString(0, 0, "VOID INVOICE")
            self.restoreState()
            self.saveState()

        # Top Accent Line
        self.setStrokeColor(TEAL_PRIMARY)
        self.setLineWidth(2.5)
        self.line(36, A4[1] - 20, A4[0] - 36, A4[1] - 20)

        # Bottom Footer Page Numbers
        self.setFont("Helvetica", 8)
        self.setFillColor(SLATE_MUTED)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 20, page_str)
        self.drawString(36, 20, "Invenza Enterprise IMS — Audited Tax Invoice")
        self.restoreState()

class InvoicePdfGenerator:
    @classmethod
    def generate_invoice_pdf(
        cls,
        invoice_data: Dict[str, Any],
        logo_path: Optional[str] = None,
        signature_path: Optional[str] = None,
    ) -> bytes:
        """
        Builds a PDF in memory and returns raw bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "InvTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=TEAL_PRIMARY,
            alignment=2,  # Right
        )
        inv_num_style = ParagraphStyle(
            "InvNum",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=SLATE_DARK,
            alignment=2,
        )
        meta_right = ParagraphStyle(
            "MetaRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=SLATE_MUTED,
            alignment=2,
        )
        company_name_style = ParagraphStyle(
            "CompanyName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=SLATE_DARK,
        )
        body_muted = ParagraphStyle(
            "BodyMuted",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=SLATE_MUTED,
        )
        body_bold = ParagraphStyle(
            "BodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11.5,
            textColor=SLATE_DARK,
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=TEAL_PRIMARY,
        )
        table_header = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white,
            alignment=1,  # Centered
        )
        table_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=SLATE_DARK,
        )
        table_cell_num = ParagraphStyle(
            "TableCellNum",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=SLATE_DARK,
            alignment=2,  # Right
        )
        table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=SLATE_DARK,
            alignment=2,
        )

        elements = []

        # --- 1. HEADER SECTION (Logo/Company Info on Left, TAX INVOICE & Meta on Right) ---
        tax_type = invoice_data.get("tax_type", "GST")
        currency_symbol = invoice_data.get("currency_symbol") or {"INR": "₹", "EUR": "€", "USD": "$"}.get(invoice_data.get("currency_code", "INR"), "₹")
        tax_label = invoice_data.get("tax_label") or {"GST": "GST", "VAT": "VAT", "SALES_TAX": "Sales Tax"}.get(tax_type, "Tax")
        tax_rate = invoice_data.get("tax_rate")
        region_disp = invoice_data.get("region_display") or invoice_data.get("place_of_supply", "")

        seller_name = invoice_data.get("seller_legal_name", "Invenza Enterprise Ltd")
        seller_addr = invoice_data.get("seller_address", "Outer Ring Road, Bengaluru, Karnataka 560103")
        seller_gstin = invoice_data.get("seller_gstin", "29AABCI1234F1Z5")
        seller_pan = invoice_data.get("seller_pan", "AABCI1234F")
        seller_state = invoice_data.get("seller_state", "Karnataka")
        seller_state_code = invoice_data.get("seller_state_code", "29")

        if tax_type == "GST":
            left_company_info = [
                Paragraph(seller_name, company_name_style),
                Paragraph(seller_addr, body_muted),
                Paragraph(f"<b>GSTIN:</b> {seller_gstin} &nbsp;&nbsp; <b>PAN:</b> {seller_pan}", body_muted),
                Paragraph(f"<b>State:</b> {seller_state} (Code: {seller_state_code})", body_muted),
            ]
        elif tax_type == "VAT":
            regime_line = str(region_disp)
            if tax_rate is not None:
                regime_line += f" — {tax_label} {float(tax_rate):g}%"
            vat_items = []
            if seller_gstin:
                vat_items.append(f"<b>USt-IdNr.:</b> {seller_gstin}")
            if seller_pan:
                vat_items.append(f"<b>Steuernummer:</b> {seller_pan}")
            left_company_info = [
                Paragraph(seller_name, company_name_style),
                Paragraph(seller_addr, body_muted),
            ]
            if vat_items:
                left_company_info.append(Paragraph(" &nbsp;&nbsp; ".join(vat_items), body_muted))
            left_company_info.append(Paragraph(f"<b>Tax Region:</b> {regime_line}", body_muted))
        else:
            regime_line = str(region_disp)
            if tax_rate is not None:
                regime_line += f" — {tax_label} {float(tax_rate):g}%"
                if tax_type == "SALES_TAX" and float(tax_rate) == 0:
                    regime_line += " (No state sales tax)"
            tax_items = []
            if seller_pan:
                tax_items.append(f"<b>EIN:</b> {seller_pan}")
            if seller_gstin:
                tax_items.append(f"<b>Tax Permit:</b> {seller_gstin}")
            left_company_info = [
                Paragraph(seller_name, company_name_style),
                Paragraph(seller_addr, body_muted),
            ]
            if tax_items:
                left_company_info.append(Paragraph(" &nbsp;&nbsp; ".join(tax_items), body_muted))
            left_company_info.append(Paragraph(f"<b>Tax Region:</b> {regime_line}", body_muted))

        inv_number = invoice_data.get("invoice_number", "INV/2026-27/00001")
        inv_date = invoice_data.get("invoice_date", "")[:10] if invoice_data.get("invoice_date") else ""
        due_date = invoice_data.get("due_date", "")[:10] if invoice_data.get("due_date") else inv_date
        place_of_supply = invoice_data.get("place_of_supply", f"{seller_state_code}-{seller_state}")
        so_number = invoice_data.get("so_number") or invoice_data.get("reference_number", "N/A")

        doc_title = invoice_data.get("document_title", "TAX INVOICE")
        num_label = invoice_data.get("number_label", "Invoice No")
        date_label = invoice_data.get("date_label", "Invoice Date")

        region_meta_label = "Place of Supply" if tax_type == "GST" else "Tax Region"
        region_meta_value = place_of_supply if tax_type == "GST" else region_disp
        right_meta_info = [
            Paragraph(doc_title, title_style),
            Paragraph(f"{num_label}: <b>{inv_number}</b>", inv_num_style),
            Paragraph(f"{date_label}: {inv_date}", meta_right),
            Paragraph(f"{region_meta_label}: <b>{region_meta_value}</b>", meta_right),
            Paragraph(f"Ref Sales Order: {so_number}", meta_right),
            Paragraph(f"Payment Terms: {invoice_data.get('payment_terms', 'Due on Receipt')}", meta_right),
        ]

        header_table = Table(
            [[left_company_info, right_meta_info]],
            colWidths=[310, 212],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        # --- 2. BILL TO & SHIP TO SECTION ---
        cust_name = invoice_data.get("customer_name", "Valued Customer")
        cust_billing = invoice_data.get("customer_billing_address", "Bengaluru, Karnataka")
        cust_shipping = invoice_data.get("customer_shipping_address", cust_billing)
        cust_gstin = invoice_data.get("customer_gstin") or "Unregistered (B2C)"
        cust_state = invoice_data.get("customer_state", "Karnataka")
        cust_code = invoice_data.get("customer_state_code", "29")

        if tax_type == "GST":
            bill_to_content = [
                Paragraph("BILL TO (BUYER DETAILS)", section_heading),
                Spacer(1, 2),
                Paragraph(cust_name, body_bold),
                Paragraph(cust_billing, body_muted),
                Paragraph(f"<b>GSTIN:</b> {cust_gstin}", body_muted),
                Paragraph(f"<b>State:</b> {cust_state} (Code: {cust_code})", body_muted),
            ]
        else:
            bill_to_content = [
                Paragraph("BILL TO (BUYER DETAILS)", section_heading),
                Spacer(1, 2),
                Paragraph(cust_name, body_bold),
                Paragraph(cust_billing, body_muted),
                Paragraph(f"<b>Tax Region:</b> {cust_state} ({cust_code})", body_muted),
            ]

        ship_to_content = [
            Paragraph("SHIP TO (DISPATCH DESTINATION)", section_heading),
            Spacer(1, 2),
            Paragraph(cust_name, body_bold),
            Paragraph(cust_shipping, body_muted),
            Paragraph(f"<b>Place of Supply:</b> {place_of_supply}", body_muted),
        ]

        parties_table = Table(
            [[bill_to_content, ship_to_content]],
            colWidths=[256, 256],
        )
        parties_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(parties_table)
        elements.append(Spacer(1, 12))

        # --- 3. LINE ITEMS TABLE WITH TAX SPLIT (GST inter/intra | VAT | Sales Tax) ---
        is_inter_state = invoice_data.get("is_inter_state", False)
        items = invoice_data.get("items", [])
        single_tax_total = float(invoice_data.get("total_single_tax", 0))
        zero_rate = tax_type == "SALES_TAX" and tax_rate is not None and float(tax_rate) == 0

        if tax_type != "GST":
            # EU VAT / US Sales Tax: single tax column, no CGST/SGST-style split
            headers = [
                Paragraph("#", table_header),
                Paragraph("Item Description", table_header),
                Paragraph("HSN/SAC" if any((it.get("hsn_code") or "").strip() for it in items) else "Ref", table_header),
                Paragraph("Qty", table_header),
                Paragraph(f"Rate ({currency_symbol})", table_header),
                Paragraph("Taxable", table_header),
                Paragraph(f"{tax_label} %", table_header),
                Paragraph(f"{tax_label} Amt", table_header),
                Paragraph(f"Total ({currency_symbol})", table_header),
            ]
            col_widths = [22, 160, 48, 38, 48, 56, 42, 52, 56]
        elif is_inter_state:
            # S.No (20), Description (152), HSN (45), Qty (35), Unit (30), Rate (45), Taxable (55), IGST Rate (35), IGST Amt (50), Total (55) = 522
            headers = [
                Paragraph("#", table_header),
                Paragraph("Item Description", table_header),
                Paragraph("HSN", table_header),
                Paragraph("Qty", table_header),
                Paragraph("Rate", table_header),
                Paragraph("Taxable Val", table_header),
                Paragraph("IGST %", table_header),
                Paragraph("IGST Amt", table_header),
                Paragraph(f"Total ({currency_symbol})", table_header),
            ]
            col_widths = [22, 160, 48, 38, 48, 56, 42, 52, 56]
        else:
            # Intra-state: CGST + SGST
            headers = [
                Paragraph("#", table_header),
                Paragraph("Item Description", table_header),
                Paragraph("HSN", table_header),
                Paragraph("Qty", table_header),
                Paragraph("Rate", table_header),
                Paragraph("Taxable", table_header),
                Paragraph("CGST", table_header),
                Paragraph("SGST", table_header),
                Paragraph(f"Total ({currency_symbol})", table_header),
            ]
            col_widths = [22, 160, 48, 38, 48, 56, 47, 47, 56]

        table_rows = [headers]

        for idx, it in enumerate(items, 1):
            desc = it.get("item_description", "Item")
            hsn = (it.get("hsn_code") or "—").strip() or "—"
            qty = f"{it.get('quantity', 1):.0f}"
            rate = f"{currency_symbol}{it.get('unit_price', 0):.2f}"
            taxable = f"{currency_symbol}{it.get('taxable_value', 0):.2f}"
            total = f"{currency_symbol}{it.get('total', 0):.2f}"

            if tax_type != "GST":
                st_r = f"{float(it.get('single_tax_rate', 0)):g}%"
                if zero_rate:
                    st_str = "0%<br/>No state sales tax"
                else:
                    st_str = f"{st_r}<br/>{currency_symbol}{it.get('single_tax_amount', 0):.2f}"
                row = [
                    Paragraph(str(idx), table_cell_num),
                    Paragraph(desc, table_cell),
                    Paragraph(hsn, table_cell),
                    Paragraph(qty, table_cell_num),
                    Paragraph(rate, table_cell_num),
                    Paragraph(taxable, table_cell_num),
                    Paragraph(st_str, table_cell_num),
                    Paragraph("", table_cell_num),
                    Paragraph(total, table_cell_bold),
                ]
            elif is_inter_state:
                igst_r = f"{float(it.get('igst_rate', 0)):g}%"
                igst_a = f"{currency_symbol}{it.get('igst_amount', 0):.2f}"
                row = [
                    Paragraph(str(idx), table_cell_num),
                    Paragraph(desc, table_cell),
                    Paragraph(hsn, table_cell),
                    Paragraph(qty, table_cell_num),
                    Paragraph(rate, table_cell_num),
                    Paragraph(taxable, table_cell_num),
                    Paragraph(igst_r, table_cell_num),
                    Paragraph(igst_a, table_cell_num),
                    Paragraph(total, table_cell_bold),
                ]
            else:
                cgst_r = f"{float(it.get('cgst_rate', 0)):g}%"
                sgst_r = f"{float(it.get('sgst_rate', 0)):g}%"
                cgst_str = f"{cgst_r}<br/>{currency_symbol}{it.get('cgst_amount', 0):.2f}"
                sgst_str = f"{sgst_r}<br/>{currency_symbol}{it.get('sgst_amount', 0):.2f}"
                row = [
                    Paragraph(str(idx), table_cell_num),
                    Paragraph(desc, table_cell),
                    Paragraph(hsn, table_cell),
                    Paragraph(qty, table_cell_num),
                    Paragraph(rate, table_cell_num),
                    Paragraph(taxable, table_cell_num),
                    Paragraph(cgst_str, table_cell_num),
                    Paragraph(sgst_str, table_cell_num),
                    Paragraph(total, table_cell_bold),
                ]
            table_rows.append(row)

        items_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SLATE_LIGHT]),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 8))

        # --- 4. TOTALS SECTION & AMOUNT IN WORDS ---
        taxable_total = float(invoice_data.get("total_taxable_value", 0))
        cgst_total = float(invoice_data.get("total_cgst", 0))
        sgst_total = float(invoice_data.get("total_sgst", 0))
        igst_total = float(invoice_data.get("total_igst", 0))
        round_off = float(invoice_data.get("round_off", 0))
        grand_total = float(invoice_data.get("grand_total", 0))
        grand_words = invoice_data.get("grand_total_words", "")

        words_box = [
            Paragraph("Total Amount in Words:", section_heading),
            Spacer(1, 2),
            Paragraph(f"<b>{grand_words}</b>", body_bold),
        ]
        bank_name = invoice_data.get("bank_name")
        if bank_name:
            words_box += [
                Spacer(1, 8),
                Paragraph("<b>Bank Remittance Details:</b>", section_heading),
                Paragraph(f"Bank Name: <b>{bank_name}</b>", body_muted),
            ]
            acct_num = invoice_data.get("bank_account_number")
            routing_code = invoice_data.get("bank_ifsc_code")
            branch = invoice_data.get("bank_branch")

            if tax_type == "VAT":
                if acct_num:
                    words_box.append(Paragraph(f"IBAN: <b>{acct_num}</b>", body_muted))
                if routing_code:
                    words_box.append(Paragraph(f"BIC / SWIFT: <b>{routing_code}</b>", body_muted))
                if branch:
                    words_box.append(Paragraph(f"Branch: {branch}", body_muted))
            elif tax_type == "SALES_TAX":
                if acct_num:
                    words_box.append(Paragraph(f"Account Number: <b>{acct_num}</b>", body_muted))
                if routing_code:
                    words_box.append(Paragraph(f"Routing (ABA): <b>{routing_code}</b>", body_muted))
                if branch:
                    words_box.append(Paragraph(f"Branch: {branch}", body_muted))
            else:
                if acct_num:
                    words_box.append(Paragraph(f"A/C Number: <b>{acct_num}</b>", body_muted))
                if routing_code:
                    words_box.append(Paragraph(f"IFSC Code: <b>{routing_code}</b>", body_muted))
                if branch:
                    words_box.append(Paragraph(f"Branch: {branch}", body_muted))

            words_box.append(Paragraph(f"Beneficiary: {invoice_data.get('account_holder_name', seller_name)}", body_muted))

        totals_rows = [
            [Paragraph("Taxable Amount:", body_muted), Paragraph(f"{currency_symbol}{taxable_total:,.2f}", table_cell_num)],
        ]
        if tax_type == "GST":
            if is_inter_state:
                totals_rows.append([Paragraph("Total IGST:", body_muted), Paragraph(f"{currency_symbol}{igst_total:,.2f}", table_cell_num)])
            else:
                totals_rows.append([Paragraph("Total CGST:", body_muted), Paragraph(f"{currency_symbol}{cgst_total:,.2f}", table_cell_num)])
                totals_rows.append([Paragraph("Total SGST:", body_muted), Paragraph(f"{currency_symbol}{sgst_total:,.2f}", table_cell_num)])
        else:
            if zero_rate:
                tax_row_label = f"Total {tax_label} (0% — No state sales tax):"
            elif tax_rate is not None:
                tax_row_label = f"Total {tax_label} ({float(tax_rate):g}%):"
            else:
                tax_row_label = f"Total {tax_label}:"
            totals_rows.append([Paragraph(tax_row_label, body_muted), Paragraph(f"{currency_symbol}{single_tax_total:,.2f}", table_cell_num)])

        if round_off != 0.0:
            totals_rows.append([Paragraph("Round Off:", body_muted), Paragraph(f"{round_off:+0.2f}", table_cell_num)])

        totals_rows.append([
            Paragraph("<b>Grand Total:</b>", ParagraphStyle("GTLabel", parent=body_bold, textColor=TEAL_DARK, fontSize=9)),
            Paragraph(f"<b>{currency_symbol}{grand_total:,.2f}</b>", ParagraphStyle("GTVal", parent=table_cell_bold, textColor=TEAL_PRIMARY, fontSize=10)),
        ])

        totals_table = Table(totals_rows, colWidths=[110, 100])
        totals_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("BACKGROUND", (0, -1), (-1, -1), TEAL_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        bottom_grid = Table(
            [[words_box, totals_table]],
            colWidths=[312, 210],
        )
        bottom_grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(bottom_grid)
        elements.append(Spacer(1, 14))

        # --- 5. FOOTER, DECLARATION & SIGNATORY ---
        signatory_name = invoice_data.get("authorized_signatory_name", "Vijay B")

        footer_notes = [
            Paragraph("<b>Declaration:</b>", section_heading),
            Paragraph("1. We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.", body_muted),
            Paragraph("2. Subject to local state jurisdiction. Interest @ 18% p.a. will be charged if payment is not made within the agreed terms.", body_muted),
            Paragraph("3. This is a cryptographically registered, computer-generated Tax Invoice under Invenza IMS.", body_muted),
        ]

        signatory_block = [
            Paragraph(f"For <b>{seller_name}</b>", ParagraphStyle("SignHeader", parent=body_bold, alignment=2)),
            Spacer(1, 28),  # Space for physical or digital signature
            Paragraph(f"<b>{signatory_name}</b>", ParagraphStyle("Signer", parent=body_bold, alignment=2)),
            Paragraph("Authorized Signatory", ParagraphStyle("SignTitle", parent=body_muted, alignment=2)),
        ]

        footer_table = Table(
            [[footer_notes, signatory_block]],
            colWidths=[332, 190],
        )
        footer_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(KeepTogether([footer_table]))

        # Build document with NumberedCanvas
        def make_canvas(*args, **kwargs):
            c = NumberedCanvas(*args, **kwargs)
            if invoice_data.get("status") == "void":
                c.is_void = True
            return c

        doc.build(elements, canvasmaker=make_canvas)
        return buffer.getvalue()
