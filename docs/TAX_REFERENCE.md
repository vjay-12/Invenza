# Invenza Tax Reference — Multi-Region Tax Configuration

This document describes the multi-currency / multi-tax system (GST / VAT / Sales Tax)
introduced for cross-region organizations.

## Core rule

> **Tax lookup is always `Country + State → tax_reference` table.**
> Currency is *never* used to determine tax rate or tax type — it is a pure
> display/billing-unit field derived from the org's country at provisioning time
> (India → INR, EU countries → EUR, United States → USD) and locked forever after.

## The `tax_reference` table

| Column | Meaning |
|---|---|
| `country_code` | ISO 3166-1 alpha-2 (`IN`, `DE`, `US`, …) |
| `state_code` | India: GST state code (`29`); US: 2-letter (`CA`); `NULL` for EU countries |
| `tax_type` | `GST` / `VAT` / `SALES_TAX` |
| `tax_rate` | Applicable standard rate (%) |
| `currency` | Display currency for the region — **informational only** |
| `is_zero_rate` | `true` for Delaware & Oregon — 0% is **rendered on invoices, never omitted** |
| `sourcing_rule` | `origin` / `destination` (US states; `NULL` elsewhere). Ohio is the seeded origin-based state |
| `last_verified_date` | Date the rate was last confirmed against an official source |
| `source_reference` | The authoritative source used for the rate |

Seeded scope: 10 EU countries (VAT) + 10 US states (Sales Tax). India is
intentionally **not** a table row — Indian GST stays product-rate-driven
(5/12/18% per SKU) with the existing CGST+SGST vs IGST split.

## ⚠️ Rate re-verification requirement

**There is no live tax-rate API.** The seeded rates are point-in-time values from
official sources (EU: European Commission "VAT rules and rates" / Taxes in Europe
Database; US: state Departments of Revenue). **EU VAT rates and US state sales-tax
rates change over time — re-verify them periodically** (suggested: quarterly)
directly against the official sources and update the rows:

```sql
UPDATE tax_reference
SET tax_rate = <new_rate>, last_verified_date = CURRENT_DATE, source_reference = '<url>'
WHERE country_code = 'XX' AND state_code = 'YY';
```

## Adding a new country or state (no code changes)

1. Insert a row into `tax_reference` (data change only — the tax engine, invoices,
   PDFs, and emails all read from this table):

   ```sql
   INSERT INTO tax_reference (id, country_code, state_code, tax_type, tax_rate, currency, is_zero_rate, sourcing_rule, last_verified_date, source_reference, created_at, updated_at)
   VALUES (gen_random_uuid(), 'PT', NULL, 'VAT', 23.00, 'EUR', FALSE, NULL, CURRENT_DATE, 'European Commission — VAT rules and rates (Portugal)', NOW(), NOW());
   ```

2. If it is a new *country* (not just a state), add it to the currency derivation
   map `COUNTRY_CURRENCY` in `backend/app/services/tax_service.py` (one-line data
   entry; if the country's currency is missing the fallback is INR, so this step
   is required for correct invoicing display).
3. Optionally add the country/state to the provisioning dropdown lists in
   `frontend/src/data/platformConstants.ts` so Super Admins can pick it in the UI.

## Tax paths (all centralized in `app/services/tax_service.py`)

| Org region | Tax | Math | Invoice rendering |
|---|---|---|---|
| India (`IN`) | GST | CGST+SGST (equal split) when org state = Invenza's registered state (Karnataka, 29), else IGST. Rate = per-product `gst_rate`. | Place of Supply, GSTIN, HSN/SAC, CGST/SGST or IGST columns |
| EU (`DE`…`LU`) | VAT | Single country rate from `tax_reference`. One "VAT" line — never a CGST/SGST split. | Country + VAT rate in the Tax Region block, `VAT` column, amount in words |
| US (`US`+state) | Sales Tax | Single state-level rate from `tax_reference`, applied once at final sale. **No input-tax-credit/reclaim mechanism** (deliberately simpler math than GST/VAT). | State + rate (or `0% — No state sales tax` for DE/OR), `Sales Tax` column |

The same engine serves all invoice types: platform Setup Fee, Monthly Maintenance,
and Sales invoices. Callers (`billing.py`, `orders.py`) never compute tax math
themselves.

## Locked org identity

`tenants.country_code`, `tenants.state`, and `tenants.currency_code` are set at
provisioning and **locked afterwards**:

- `PUT /api/v1/superadmin/companies/{id}` returns `400` for any change attempt.
- Org-level Settings/Profile never expose these fields.
- Provisioning validates: country must be `IN` or present in `tax_reference`;
  US orgs must pick one of the 10 seeded states; EU orgs have no state.

## US state-level rate scope

Seeded US rates are **state-level general rates** (e.g. California 7.25%).
County/city/local surcharges are out of scope at this stage; Ohio is seeded as
the origin-sourcing edge case, Delaware and Oregon as zero-rate edge cases.

## Verification tooling

- `backend/seed_multitax_test_orgs.py` — provisions DE/CA/Delaware test orgs,
  generates invoices through the real service path, asserts rates/totals, renders
  PDFs to `backend/scratch/`, and regression-checks an existing INR org.
- `backend/test_multitax_billing.py` — live API acceptance test (requires the API
  running on `127.0.0.1:8000`): provisioning validation, VAT/Sales-Tax/0% math,
  INR regression, locked-field 400s, per-currency aggregates.
