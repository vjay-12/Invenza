"""
GST Calculation Engine and Indian Currency Number-to-Words Converter.
Provides accurate intra-state (CGST + SGST) vs inter-state (IGST) split logic,
per-line item tax computations, standard GST rounding, and Indian numbering conversion.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Tuple

INDIAN_STATES = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu",
    "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}

ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen"
]

TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
]

def _two_digits_to_words(n: int) -> str:
    if n == 0:
        return ""
    if n < 20:
        return ONES[n]
    tens_part = TENS[n // 10]
    ones_part = ONES[n % 10]
    return f"{tens_part} {ones_part}".strip()

def _three_digits_to_words(n: int) -> str:
    hundreds = n // 100
    remainder = n % 100
    parts = []
    if hundreds > 0:
        parts.append(f"{ONES[hundreds]} Hundred")
    if remainder > 0:
        parts.append(_two_digits_to_words(remainder))
    return " ".join(parts).strip()

def amount_to_indian_words(amount: float) -> str:
    """
    Converts a currency amount into words according to Indian numbering convention
    (Crores, Lakhs, Thousands, Hundreds).
    e.g. 12450.00 -> 'Rupees Twelve Thousand Four Hundred Fifty Only'
    """
    if amount is None or amount == 0:
        return "Rupees Zero Only"

    dec_amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rupees = int(dec_amount)
    paise = int(round((dec_amount - Decimal(rupees)) * 100))

    if rupees == 0 and paise == 0:
        return "Rupees Zero Only"

    parts = []

    if rupees > 0:
        # Crores (10,000,000)
        crores = rupees // 10000000
        rupees %= 10000000
        if crores > 0:
            parts.append(f"{amount_to_indian_words(crores).replace('Rupees ', '').replace(' Only', '')} Crore")

        # Lakhs (100,000)
        lakhs = rupees // 100000
        rupees %= 100000
        if lakhs > 0:
            parts.append(f"{_two_digits_to_words(lakhs)} Lakh")

        # Thousands (1,000)
        thousands = rupees // 1000
        rupees %= 1000
        if thousands > 0:
            parts.append(f"{_two_digits_to_words(thousands)} Thousand")

        # Hundreds and Remainder
        if rupees > 0:
            parts.append(_three_digits_to_words(rupees))

        rupees_str = " ".join(parts).strip()
        result = f"Rupees {rupees_str}"
    else:
        result = ""

    if paise > 0:
        paise_str = _two_digits_to_words(paise)
        if result:
            result = f"{result} and {paise_str} Paise"
        else:
            result = f"{paise_str} Paise"

    return f"{result} Only".strip()

class GSTService:
    @staticmethod
    def normalize_state_code(code_or_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolves state code (e.g. '29') and state name (e.g. 'Karnataka').
        Returns (code, name) or (None, None) if unresolved.
        """
        if not code_or_name or not str(code_or_name).strip():
            return None, None

        clean = str(code_or_name).strip()

        # Handle '29 - Karnataka' or '29-Karnataka' or 'Karnataka (29)'
        if "-" in clean:
            parts = [p.strip() for p in clean.split("-") if p.strip()]
            for p in parts:
                c, n = GSTService.normalize_state_code(p)
                if c:
                    return c, n

        # Check exact code match (e.g. '29' or '07')
        padded = clean.zfill(2) if clean.isdigit() and len(clean) <= 2 else clean
        if padded in INDIAN_STATES:
            return padded, INDIAN_STATES[padded]

        # Check exact or case-insensitive state name
        for code, name in INDIAN_STATES.items():
            if name.lower() == clean.lower():
                return code, name

        # Check if any state name appears inside the text (e.g. address string)
        lower_text = clean.lower()
        sorted_states = sorted(INDIAN_STATES.items(), key=lambda x: len(x[1]), reverse=True)
        for code, name in sorted_states:
            if name.lower() in lower_text:
                return code, name

        return None, None

    @staticmethod
    def resolve_place_of_supply(
        billing_state: Optional[str] = None,
        billing_state_code: Optional[str] = None,
        billing_address: Optional[str] = None,
        shipping_state: Optional[str] = None,
        shipping_state_code: Optional[str] = None,
        shipping_address: Optional[str] = None,
        customer_gstin: Optional[str] = None,
        legacy_state: Optional[str] = None,
        legacy_state_code: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Implements statutory Place of Supply resolution rules:
        1. If a shipping/delivery address is provided and its state differs from the billing state,
           use the SHIPPING state as the place of supply (goods movement terminates there).
        2. If no separate shipping address is given, use the billing state as the place of supply.
        3. If the customer is unregistered (no GSTIN) and only an address on the invoice is available,
           use that invoice address's state as the place of supply.
        """
        # Resolve billing
        b_code, b_name = None, None
        for val in [billing_state_code, billing_state, billing_address]:
            if val:
                c, n = GSTService.normalize_state_code(val)
                if c:
                    b_code, b_name = c, n
                    break

        # Resolve shipping
        s_code, s_name = None, None
        for val in [shipping_state_code, shipping_state, shipping_address]:
            if val:
                c, n = GSTService.normalize_state_code(val)
                if c:
                    s_code, s_name = c, n
                    break

        # Check legacy state fallback
        leg_code, leg_name = None, None
        for val in [legacy_state_code, legacy_state]:
            if val:
                c, n = GSTService.normalize_state_code(val)
                if c:
                    leg_code, leg_name = c, n
                    break

        # Rule 1: Shipping address/state provided
        # If shipping state is specified or shipping address differs from billing address
        has_shipping = bool(shipping_state or shipping_state_code or (shipping_address and shipping_address.strip() != (billing_address or "").strip()))
        if has_shipping and s_code:
            return s_code, s_name

        # Rule 2: No separate shipping address -> use billing state
        if b_code:
            return b_code, b_name

        # Rule 3: Unregistered customer / only invoice address given
        if s_code:
            return s_code, s_name
        if leg_code:
            return leg_code, leg_name

        return None, None

    @staticmethod
    def calculate_tax_split(
        taxable_amount: float,
        gst_rate: float = 18.0,
        seller_state: str = "Karnataka",
        customer_state: str = "Karnataka",
    ) -> Dict[str, Any]:
        """
        Unified scalar GST split calculator for any platform billing, setup fee, or service invoice.
        Intra-state (same state): CGST (half) + SGST (half), IGST = 0.
        Inter-state (diff state): IGST (full), CGST = 0, SGST = 0.
        """
        s_code, s_name = GSTService.normalize_state_code(seller_state)
        pos_code, pos_name = GSTService.normalize_state_code(customer_state)
        if not s_code:
            s_code, s_name = "29", "Karnataka"
        if not pos_code:
            pos_code, pos_name = "29", "Karnataka"

        is_inter = (s_code != pos_code)
        amt = Decimal(str(taxable_amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rate = Decimal(str(gst_rate or 0))

        if rate == Decimal("0") or amt == Decimal("0"):
            cgst_amt = Decimal("0.00")
            sgst_amt = Decimal("0.00")
            igst_amt = Decimal("0.00")
            cgst_rate = Decimal("0.00")
            sgst_rate = Decimal("0.00")
            igst_rate = Decimal("0.00")
        elif is_inter:
            cgst_amt = Decimal("0.00")
            sgst_amt = Decimal("0.00")
            cgst_rate = Decimal("0.00")
            sgst_rate = Decimal("0.00")
            igst_rate = rate
            igst_amt = (amt * (igst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            cgst_rate = (rate / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sgst_rate = cgst_rate
            igst_rate = Decimal("0.00")
            cgst_amt = (amt * (cgst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sgst_amt = (amt * (sgst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            igst_amt = Decimal("0.00")

        total = amt + cgst_amt + sgst_amt + igst_amt
        return {
            "is_inter_state": is_inter,
            "seller_state": s_name,
            "seller_state_code": s_code,
            "customer_state": pos_name,
            "customer_state_code": pos_code,
            "place_of_supply": f"{pos_code} - {pos_name}",
            "taxable_amount": float(amt),
            "gst_rate": float(rate),
            "cgst_rate": float(cgst_rate),
            "cgst_amount": float(cgst_amt),
            "sgst_rate": float(sgst_rate),
            "sgst_amount": float(sgst_amt),
            "igst_rate": float(igst_rate),
            "igst_amount": float(igst_amt),
            "total_amount": float(total),
        }

    @staticmethod
    def calculate_invoice_taxes(
        seller_state_code: str,
        place_of_supply_state_code: str,
        line_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Computes line-by-line GST tax split and totals.
        - Seller state == place of supply state -> CGST (50%) + SGST (50%)
        - Seller state != place of supply state -> IGST (100%)
        - 0% GST rate handled cleanly without tax.
        """
        s_code, s_name = GSTService.normalize_state_code(seller_state_code)
        pos_code, pos_name = GSTService.normalize_state_code(place_of_supply_state_code)

        if not s_code:
            raise ValueError(f"Tenant/Seller registered business state is invalid or missing: '{seller_state_code}'")
        if not pos_code:
            raise ValueError(f"Customer Place of Supply state is invalid or missing: '{place_of_supply_state_code}'")

        is_inter_state = (s_code != pos_code)

        calculated_items = []
        total_taxable_value = Decimal("0.00")
        total_cgst = Decimal("0.00")
        total_sgst = Decimal("0.00")
        total_igst = Decimal("0.00")

        for it in line_items:
            qty = Decimal(str(it.get("quantity") or it.get("ordered_qty") or 0))
            unit_price = Decimal(str(it.get("unit_price") or 0))
            discount = Decimal(str(it.get("discount") or 0))
            raw_gst = it.get("gst_rate")
            gst_rate = Decimal(str(raw_gst if raw_gst is not None else 18.00))

            taxable_val = ((unit_price * qty) - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if taxable_val < Decimal("0.00"):
                taxable_val = Decimal("0.00")

            total_taxable_value += taxable_val

            if gst_rate == Decimal("0.00"):
                cgst_rate = Decimal("0.00")
                cgst_amt = Decimal("0.00")
                sgst_rate = Decimal("0.00")
                sgst_amt = Decimal("0.00")
                igst_rate = Decimal("0.00")
                igst_amt = Decimal("0.00")
            elif is_inter_state:
                cgst_rate = Decimal("0.00")
                cgst_amt = Decimal("0.00")
                sgst_rate = Decimal("0.00")
                sgst_amt = Decimal("0.00")
                igst_rate = gst_rate
                igst_amt = (taxable_val * (igst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_igst += igst_amt
            else:
                cgst_rate = (gst_rate / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                cgst_amt = (taxable_val * (cgst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                sgst_rate = cgst_rate
                sgst_amt = (taxable_val * (sgst_rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                igst_rate = Decimal("0.00")
                igst_amt = Decimal("0.00")
                total_cgst += cgst_amt
                total_sgst += sgst_amt

            line_total = (taxable_val + cgst_amt + sgst_amt + igst_amt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            calculated_items.append({
                "product_id": it.get("product_id"),
                "item_description": it.get("item_description") or it.get("name") or "Product SKU",
                "hsn_code": it.get("hsn_code") or "8471",
                "quantity": float(qty),
                "unit_of_measure": it.get("unit_of_measure") or "pcs",
                "unit_price": float(unit_price),
                "discount": float(discount),
                "taxable_value": float(taxable_val),
                "gst_rate": float(gst_rate),
                "cgst_rate": float(cgst_rate),
                "cgst_amount": float(cgst_amt),
                "sgst_rate": float(sgst_rate),
                "sgst_amount": float(sgst_amt),
                "igst_rate": float(igst_rate),
                "igst_amount": float(igst_amt),
                "total": float(line_total),
            })

        # Calculate invoice level aggregates and round-off to nearest rupee
        raw_grand_total = total_taxable_value + total_cgst + total_sgst + total_igst
        rounded_grand_total = raw_grand_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        round_off = (rounded_grand_total - raw_grand_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        words = amount_to_indian_words(float(rounded_grand_total))

        return {
            "is_inter_state": is_inter_state,
            "seller_state": s_name,
            "seller_state_code": s_code,
            "customer_state": pos_name,
            "customer_state_code": pos_code,
            "place_of_supply": f"{pos_code} - {pos_name}",
            "items": calculated_items,
            "total_taxable_value": float(total_taxable_value),
            "total_cgst": float(total_cgst),
            "total_sgst": float(total_sgst),
            "total_igst": float(total_igst),
            "round_off": float(round_off),
            "grand_total": float(rounded_grand_total),
            "grand_total_words": words,
        }
