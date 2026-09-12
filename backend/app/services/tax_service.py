"""
Centralized multi-regime tax engine: GST (India) / VAT (EU) / Sales Tax (US).

This module is the SINGLE entry point for tax computation across every invoice
type (platform setup fee, monthly maintenance, sales invoices). Do NOT implement
tax math in endpoints — call TaxService.calculate().

Lookup rule: Country + State -> TaxReference table. Currency is display-only and
is derived from the country (never used to pick a rate or tax type).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax_reference import TaxReference
from app.models.tenant import Tenant
from app.services.gst_service import GSTService, amount_to_indian_words, ONES, TENS

TAX_TYPE_GST = "GST"
TAX_TYPE_VAT = "VAT"
TAX_TYPE_SALES_TAX = "SALES_TAX"

TAX_LABELS = {
    TAX_TYPE_GST: "GST",
    TAX_TYPE_VAT: "VAT",
    TAX_TYPE_SALES_TAX: "Sales Tax",
}

CURRENCY_SYMBOLS = {"INR": "₹", "EUR": "€", "USD": "$"}

# Country -> display currency. Currency is DERIVED from country at provisioning
# and locked; it must never influence tax rate or tax type.
COUNTRY_CURRENCY = {
    "IN": "INR",
    "US": "USD",
    "DE": "EUR", "FR": "EUR", "NL": "EUR", "IE": "EUR", "ES": "EUR",
    "IT": "EUR", "BE": "EUR", "PL": "EUR", "SE": "EUR", "LU": "EUR",
}

COUNTRY_NAMES = {
    "IN": "India", "US": "United States",
    "DE": "Germany", "FR": "France", "NL": "Netherlands", "IE": "Ireland",
    "ES": "Spain", "IT": "Italy", "BE": "Belgium", "PL": "Poland",
    "SE": "Sweden", "LU": "Luxembourg",
}

# US states in the initial provisioning scope (mirrors TaxReference US seed rows).
US_STATES = {
    "CA": "California", "TX": "Texas", "NY": "New York", "FL": "Florida",
    "IL": "Illinois", "WA": "Washington", "GA": "Georgia", "OH": "Ohio",
    "DE": "Delaware", "OR": "Oregon",
}

SUPPORTED_PROVISIONING_COUNTRIES = ["IN"] + sorted(COUNTRY_NAMES.keys() - {"IN", "US"}) + ["US"]


def derive_currency(country_code: str) -> str:
    return COUNTRY_CURRENCY.get((country_code or "IN").upper(), "INR")


def currency_symbol(currency_code: str) -> str:
    return CURRENCY_SYMBOLS.get((currency_code or "INR").upper(), "₹")


def country_name(country_code: str) -> str:
    return COUNTRY_NAMES.get((country_code or "").upper(), (country_code or "").upper())


def _three_digits_to_words(n: int) -> str:
    parts = []
    hundreds, remainder = divmod(n, 100)
    if hundreds > 0:
        parts.append(f"{ONES[hundreds]} Hundred")
    if remainder > 0:
        if remainder < 20:
            parts.append(ONES[remainder])
        else:
            tens_part = TENS[remainder // 10]
            ones_part = ONES[remainder % 10]
            parts.append(f"{tens_part} {ones_part}".strip())
    return " ".join(parts).strip()


def _int_to_words(n: int) -> str:
    """Western scale (thousand / million / billion) number-to-words."""
    if n == 0:
        return "Zero"
    groups = []
    for scale in [10**9, 10**6, 10**3]:
        if n >= scale:
            groups.append(f"{_int_to_words(n // scale)} { {10**9: 'Billion', 10**6: 'Million', 10**3: 'Thousand'}[scale] }")
            n %= scale
    if n > 0:
        groups.append(_three_digits_to_words(n))
    return " ".join(groups).strip()


def amount_to_words(amount: float, currency_code: str = "INR") -> str:
    """Amount in words: Indian convention for INR, western scale for EUR/USD."""
    if (currency_code or "INR").upper() == "INR":
        return amount_to_indian_words(amount)
    major_name, minor_name = {"EUR": ("Euros", "Cents"), "USD": ("Dollars", "Cents")}.get(
        (currency_code or "").upper(), ("Units", "Cents")
    )
    if amount is None or amount == 0:
        return f"Zero {major_name} Only"
    dec = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    units = int(dec)
    cents = int(round((dec - Decimal(units)) * 100))
    result = f"{_int_to_words(units)} {major_name}" if units > 0 else ""
    if cents > 0:
        result = f"{result} and {_int_to_words(cents)} {minor_name}" if result else f"{_int_to_words(cents)} {minor_name}"
    return f"{result} Only"


def resolve_us_state(state_input: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Resolves a US state name or 2-letter code -> (code, name)."""
    if not state_input or not str(state_input).strip():
        return None, None
    clean = str(state_input).strip()
    upper = clean.upper()
    if upper in US_STATES:
        return upper, US_STATES[upper]
    for code, name in US_STATES.items():
        if name.lower() == clean.lower():
            return code, name
    return None, None


def resolve_org_state(country_code: str, state_input: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Country-aware org state resolution. IN: GST codes; US: state names/codes; EU: none."""
    cc = (country_code or "IN").upper()
    if cc == "IN":
        return GSTService.normalize_state_code(state_input)
    if cc == "US":
        return resolve_us_state(state_input)
    return None, None


async def get_org_tax_context(db: AsyncSession, tenant_id) -> Dict[str, Any]:
    """
    Fetches the org's locked tax identity: country, resolved state, derived currency,
    and the TaxReference row for EU/US orgs (None for India — GST is product-rate-driven).
    """
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant organization not found.")

    country = (tenant.country_code or "IN").upper()
    currency = derive_currency(country)

    if country == "IN":
        state_code, state_name = GSTService.normalize_state_code(tenant.state)
        return {
            "country_code": "IN", "state_code": state_code, "state_name": state_name,
            "currency": currency, "currency_code": currency,
            "tax_type": TAX_TYPE_GST, "tax_label": TAX_LABELS[TAX_TYPE_GST],
            "company_name": tenant.name, "country_name": "India",
            "tax_ref": None, "tenant": tenant,
        }

    state_code, state_name = resolve_org_state(country, tenant.state)
    ref_q = select(TaxReference).where(TaxReference.country_code == country)
    if country == "US":
        if not state_code:
            raise HTTPException(
                status_code=400,
                detail=f"US organization is missing a valid registered state (expected one of: {', '.join(US_STATES)}).",
            )
        ref_q = ref_q.where(TaxReference.state_code == state_code)
    else:
        ref_q = ref_q.where(TaxReference.state_code.is_(None))
    tax_ref = (await db.execute(ref_q)).scalar_one_or_none()
    if not tax_ref:
        raise HTTPException(
            status_code=400,
            detail=f"No {TAX_LABELS.get(tax_ref_type(country), 'tax')} rate configured for {country_name(country)}"
                   f"{' / ' + state_name if state_name else ''}. Add a TaxReference row (data change, no code change).",
        )
    tax_type = tax_ref.tax_type if tax_ref and tax_ref.tax_type else tax_ref_type(country)
    return {
        "country_code": country, "state_code": state_code, "state_name": state_name,
        "currency": currency, "currency_code": currency,
        "tax_type": tax_type, "tax_label": TAX_LABELS.get(tax_type, tax_type),
        "company_name": tenant.name, "country_name": country_name(country),
        "tax_ref": tax_ref, "tenant": tenant,
    }


def tax_ref_type(country_code: str) -> str:
    cc = (country_code or "").upper()
    if cc == "IN":
        return TAX_TYPE_GST
    if cc == "US":
        return TAX_TYPE_SALES_TAX
    return TAX_TYPE_VAT


def region_display(context: Dict[str, Any]) -> str:
    """Human region string for invoices: 'Germany (DE)', 'California (US-CA)', 'US-DE - Delaware'."""
    cc = context["country_code"]
    if cc == "IN":
        if context.get("state_code") and context.get("state_name"):
            return f"{context['state_code']} - {context['state_name']}"
        return "29 - Karnataka"
    if cc == "US":
        return f"US-{context['state_code']} - {context['state_name']}"
    return f"{cc} - {country_name(cc)}"


class TaxService:
    """Single entry point for invoice tax computation across all regimes."""

    @staticmethod
    async def calculate(
        db: AsyncSession,
        *,
        tenant_id,
        line_items: List[Dict[str, Any]],
        seller_state_code: Optional[str] = None,
        place_of_supply_state_code: Optional[str] = None,
        is_waived: bool = False,
    ) -> Dict[str, Any]:
        context = await get_org_tax_context(db, tenant_id)
        country = context["country_code"]
        currency = context["currency"]

        if country == "IN":
            seller = seller_state_code or context.get("state_code") or "29"
            pos = place_of_supply_state_code or context.get("state_code") or "29"
            calc = GSTService.calculate_invoice_taxes(seller, pos, line_items)
            if is_waived:
                calc = TaxService._zeroed(calc)
            calc.update({
                "tax_type": TAX_TYPE_GST,
                "tax_label": TAX_LABELS[TAX_TYPE_GST],
                "tax_rate": None,
                "currency_code": "INR",
                "currency_symbol": currency_symbol("INR"),
                "region_display": calc["place_of_supply"],
                "sourcing_rule": None,
                "total_single_tax": 0.0,
            })
            return calc

        tax_ref = context["tax_ref"]
        rate = Decimal("0.00") if is_waived else Decimal(str(tax_ref.tax_rate))
        reg = region_display(context)

        items = []
        total_taxable = Decimal("0.00")
        total_tax = Decimal("0.00")
        for it in line_items:
            qty = Decimal(str(it.get("quantity") or it.get("ordered_qty") or 0))
            unit_price = Decimal(str(it.get("unit_price") or 0))
            discount = Decimal(str(it.get("discount") or 0))
            taxable = ((unit_price * qty) - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if taxable < Decimal("0.00"):
                taxable = Decimal("0.00")
            tax_amt = (taxable * (rate / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            line_total = (taxable + tax_amt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_taxable += taxable
            total_tax += tax_amt
            items.append({
                "product_id": it.get("product_id"),
                "item_description": it.get("item_description") or it.get("name") or "Service",
                "hsn_code": it.get("hsn_code") or "",
                "quantity": float(qty),
                "unit_of_measure": it.get("unit_of_measure") or "service",
                "unit_price": float(unit_price),
                "discount": float(discount),
                "taxable_value": float(taxable),
                "gst_rate": float(rate),  # regional rate (column reused; GST columns stay 0)
                "cgst_rate": 0.0, "cgst_amount": 0.0,
                "sgst_rate": 0.0, "sgst_amount": 0.0,
                "igst_rate": 0.0, "igst_amount": 0.0,
                "single_tax_rate": float(rate),
                "single_tax_amount": float(tax_amt),
                "total": float(line_total),
            })

        raw_total = total_taxable + total_tax
        rounded_total = raw_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        round_off = (rounded_total - raw_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "tax_type": tax_ref.tax_type,
            "tax_label": TAX_LABELS.get(tax_ref.tax_type, tax_ref.tax_type),
            "tax_rate": float(rate),
            "currency_code": currency,
            "currency_symbol": currency_symbol(currency),
            "region_display": reg,
            "place_of_supply": reg,
            "sourcing_rule": tax_ref.sourcing_rule,
            "is_zero_rate": bool(tax_ref.is_zero_rate),
            "is_inter_state": False,
            "seller_state": country_name(country) if country != "US" else context.get("state_name"),
            "seller_state_code": context.get("state_code") if country == "US" else country,
            "customer_state": country_name(country) if country != "US" else context.get("state_name"),
            "customer_state_code": context.get("state_code") if country == "US" else country,
            "items": items,
            "total_taxable_value": float(total_taxable),
            "total_single_tax": float(total_tax),
            "total_cgst": 0.0, "total_sgst": 0.0, "total_igst": 0.0,
            "round_off": float(round_off),
            "grand_total": float(rounded_total),
            "grand_total_words": amount_to_words(float(rounded_total), currency),
        }

    @staticmethod
    def _zeroed(calc: Dict[str, Any]) -> Dict[str, Any]:
        """Waived record: zero every amount while keeping structure and labels."""
        calc = dict(calc)
        calc["items"] = [dict(it, taxable_value=0.0, cgst_amount=0.0, sgst_amount=0.0,
                              igst_amount=0.0, single_tax_amount=0.0, total=0.0) for it in calc.get("items", [])]
        calc.update({
            "total_taxable_value": 0.0, "total_cgst": 0.0, "total_sgst": 0.0,
            "total_igst": 0.0, "total_single_tax": 0.0, "round_off": 0.0, "grand_total": 0.0,
            "grand_total_words": amount_to_indian_words(0),
        })
        return calc


def validate_product_tax_for_org(
    org_context: Dict[str, Any],
    tax_code: Optional[str],
    tax_rate: Optional[float],
) -> Tuple[Optional[str], float]:
    """
    Validates and standardizes product tax_code and tax_rate against the organization's locked tax configuration.
    
    Enforces:
    - India (GST):
        * tax_code (HSN/SAC) is REQUIRED. Cannot be blank or whitespace.
        * tax_rate must be a valid statutory Indian GST slab: 0%, 5%, 12%, 18%, 28%, 40% (or 0.25%, 3%).
          Defaults to 18.0% if omitted.
    - Germany / EU (VAT):
        * tax_code is OPTIONAL. Blank/None is fully allowed; if supplied, accepted as Taric/Commodity code.
        * tax_rate accepts any valid numeric percentage relevant to the locked EU tax configuration
          (standard rate e.g. 19% for Germany, reduced rates e.g. 7%, or zero 0%). Valid range: 0% to 30%.
          Defaults to the org's locked standard VAT rate if omitted.
    - US (Sales Tax):
        * tax_code is OPTIONAL / NOT APPLICABLE (sales taxes have no classification code). Blank/None allowed.
        * If the state is statutory 0% (Delaware, Oregon), tax_rate must be 0.0%.
        * For standard US states (California 7.25%, etc.), tax_rate must be between 0% and 15%.
          Defaults to the org's locked state sales tax rate if omitted.
    """
    country = org_context.get("country_code", "IN").upper()
    tax_type = tax_ref_type(country)
    tax_ref = org_context.get("tax_ref")

    # 1. Clean tax_code
    clean_code = str(tax_code).strip() if tax_code is not None else ""

    # 2. Validate tax_code by regime
    if tax_type == TAX_TYPE_GST:
        if not clean_code:
            raise HTTPException(
                status_code=400,
                detail="tax_code (HSN/SAC) is required for Indian GST organizations. Please provide a valid code (e.g. '8471').",
            )
        resolved_code: Optional[str] = clean_code
    else:
        # EU VAT and US Sales Tax: tax_code is optional/not applicable
        resolved_code = clean_code if clean_code else None

    # 3. Resolve default tax_rate if omitted
    if tax_rate is None:
        if tax_type == TAX_TYPE_GST:
            rate_val = 18.0
        elif tax_ref and tax_ref.tax_rate is not None:
            rate_val = float(tax_ref.tax_rate)
        else:
            rate_val = 0.0
    else:
        try:
            rate_val = float(tax_rate)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tax_rate '{tax_rate}'. Must be a valid numeric percentage.",
            )

    # 4. Validate tax_rate by regime
    if tax_type == TAX_TYPE_GST:
        valid_gst_slabs = [0.0, 0.25, 3.0, 5.0, 12.0, 18.0, 28.0, 40.0]
        # Allow rounding tolerance
        if not any(abs(rate_val - slab) < 0.001 for slab in valid_gst_slabs):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid GST rate: {rate_val}%. Allowed GST rates for India are 0%, 5%, 12%, 18%, 28%, 40%.",
            )
    elif tax_type == TAX_TYPE_VAT:
        if rate_val < 0.0 or rate_val > 30.0:
            c_name = country_name(country)
            std_rate = float(tax_ref.tax_rate) if tax_ref else 19.0
            raise HTTPException(
                status_code=400,
                detail=f"Invalid VAT rate: {rate_val}%. Applicable VAT rates for {c_name} must be between 0% and 30% (standard rate: {std_rate}%).",
            )
    elif tax_type == TAX_TYPE_SALES_TAX:
        state_name = org_context.get("state_name") or "US"
        is_zero = bool(tax_ref.is_zero_rate) if tax_ref else False
        if is_zero and abs(rate_val) > 0.001:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Sales Tax rate: {rate_val}%. {state_name} is a statutory 0% sales tax jurisdiction.",
            )
        if rate_val < 0.0 or rate_val > 15.0:
            std_rate = float(tax_ref.tax_rate) if tax_ref else 0.0
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Sales Tax rate: {rate_val}%. Applicable Sales Tax rates for {state_name} must be between 0% and 15% (state standard: {std_rate}%).",
            )

    return resolved_code, rate_val

