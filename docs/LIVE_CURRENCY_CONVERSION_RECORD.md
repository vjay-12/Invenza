# Live Currency Conversion Feature: Architecture & Implementation Record

> **Status**: Deferred to a future release  
> **Date Documented**: September 9, 2026  
> **Reason for Deferral**: Decommissioned to prevent unintentional database price mutations and data desynchronization across multi-tenant ledgers until a native dual-ledger currency model is established.

---

## 1. Overview & Architecture Summary

The Invenza Multi-Currency Conversion feature was implemented as a real-time Forex service allowing tenant administrators to switch their operating base currency between:
- **USD ($)**: United States Dollar (Default Base)
- **EUR (€)**: Euro
- **INR (₹)**: Indian Rupee

It comprised:
1. An external public Forex data feed (**Frankfurter API**).
2. A resilient backend caching micro-service in FastAPI with **Redis 1-Hour TTL Caching** and process-level in-memory fallback.
3. An active client-side synchronization engine in **React (`InventoryContext.tsx`)** that polled rates, formatted currencies, and recalculated product catalogs, Purchase Orders, Sales Orders, and Stock Movements.
4. A frontend UI in **Settings (`Settings.tsx`)** providing live exchange rate tickers, 3-way sample conversion benchmark cards, and tenant currency toggle buttons.

---

## 2. External API: Frankfurter API

- **Service**: Frankfurter (Open-source foreign exchange rates published by the European Central Bank)
- **Base Endpoint**: `https://api.frankfurter.app/latest?from=USD&to=EUR,INR`
- **Request Method**: HTTP GET
- **Authentication**: None required (Public API)
- **Request Headers**:
  ```python
  headers = {
      "User-Agent": "Invenza-IMS/1.0 (https://invenza.internal; inventory-exchange-service)",
      "Accept": "application/json",
  }
  ```
- **Response Format**:
  ```json
  {
    "amount": 1.0,
    "base": "USD",
    "date": "2026-09-08",
    "rates": {
      "EUR": 0.8604,
      "INR": 94.49
    }
  }
  ```

---

## 3. Backend Implementation Details

### A. Endpoint Registration
- Route file: `backend/app/api/v1/endpoints/exchange_rates.py`
- Main router integration: Mounted at both `/api/v1/exchange-rates` (via `api_router` in `api.py`) and `/api/exchange-rates` (direct mount in `main.py`).

### B. Redis & In-Memory Caching Architecture
To guarantee low latency (<5ms) and minimize external API rate limits, a dual-layer caching strategy was implemented:
- **Redis Cache Key**: `invenza:cache:exchange_rates` (TTL: `3600` seconds / 1 hour).
- **Redis Fallback Key**: `invenza:cache:exchange_rates:last_known` (No TTL expiration; survives external outages).
- **Process Memory Cache**: Module-level variables `_memory_cache`, `_memory_cache_expiry`, and `_last_known_rates` used whenever Redis was temporarily unavailable.

### C. Backend Endpoint Logic (`GET /api/v1/exchange-rates`)
1. **Tier 1 (Redis Cache)**: Check `await redis.get("invenza:cache:exchange_rates")`. If present, return with `"cached": True`.
2. **Tier 2 (In-Memory)**: If Redis is unavailable, check `_memory_cache` against `_memory_cache_expiry`.
3. **Tier 3 (Frankfurter Fetch)**: On cache miss or expiry, call `fetch_from_frankfurter()` with a 10s timeout using `httpx.AsyncClient`.
   - On success: Write to Redis with 1h TTL (`setex`), update `invenza:cache:exchange_rates:last_known`, and return `"cached": False`.
4. **Tier 4 (Stale Fallback)**: If Frankfurter call fails, fetch `invenza:cache:exchange_rates:last_known` from Redis or `_last_known_rates` in memory, returning `"status": "cached_fallback"`.
5. **Tier 5 (Graceful Failure)**: If completely unavailable, return JSON with `"status": "unavailable"`.

---

## 4. Frontend Integration & Wiring

### A. API Service (`frontend/src/services/api.ts`)
```typescript
getExchangeRates: async () => {
  try {
    const res = await fetch('/api/exchange-rates');
    if (res.ok) return await res.json();
  } catch {
    // fallback to versioned route
  }
  return fetchWithFallback<any>('/exchange-rates');
}
```

### B. Inventory Context (`frontend/src/context/InventoryContext.tsx`)
- **State Trackers**:
  - `currency`: Tracked active `CurrencyCode` (`'USD' | 'EUR' | 'INR'`), initialized from `localStorage.getItem('invenza_active_currency')`.
  - `exchangeRates`: Held current rates with fallback defaults (`USD: 1.0, EUR: 0.8604, INR: 94.49`).
  - `ratesStatus`: `'live' | 'cached' | 'unavailable' | 'loading'`.
  - `refreshExchangeRates()`: Asynchronously queried `api.getExchangeRates()` on mount.
- **Conversion Math (`convertAmount`)**:
  ```typescript
  const convertAmount = (amount: number, from: CurrencyCode, to: CurrencyCode) => {
    if (from === to) return amount;
    const inUSD = amount / (exchangeRates[from] || 1);
    return inUSD * (exchangeRates[to] || 1);
  };
  ```
- **Mutation Logic (`setCurrency`)**:
  - Re-calculated monetary fields on all `products` (`costPrice`, `sellPrice`).
  - Re-calculated all `purchaseOrders` (`totalAmount`, `unitCost`).
  - Re-calculated all `salesOrders` (`totalAmount`, `unitPrice`).
  - Re-calculated all `ledger` movements (`unitCost`).
  - Synced transformed amounts to `localStorage` and sent asynchronous `api.updateProduct` updates to PostgreSQL.

### C. Settings Page (`frontend/src/pages/Settings.tsx`)
- **Section 1: Tenant Base Currency**:
  - 3 large selectable cards for USD, EUR, and INR displaying symbols, currency codes, and active checkmarks.
  - Success banner displaying the effective conversion rate and the number of SKUs updated.
  - **Live Forex Rate Stream Bar**: Displayed animated pulsating status dot, live rates (`1 USD = X EUR • 1 USD = Y INR`), Redis cache badge (`Redis Cached (1h)`), and Frankfurter timestamp.
  - **3-Way Benchmark Cards**: Rendered sample $100.00 USD converted live into Euro and Rupee equivalents.

---

## 5. Architectural Issues Identified & Reason for Decommissioning

1. **Destructive Price Mutation**:
   Mutating the persistent `cost_price` and `sell_price` columns in PostgreSQL on every currency toggle introduces floating-point rounding drift (`toFixed(2)`), permanently corrupting master SKU unit costs over multiple switches.
2. **Desynchronization with Historical Invoices & Orders**:
   Sales invoices, GST tax percentages, and historical accounting ledgers must remain immutable in their transaction-time currency. Converting active database entities risked serious audit inconsistencies.
3. **Preferred Future Architecture**:
   In a future release, multi-currency support should be implemented via:
   - Fixed base currency per tenant stored at provisioning.
   - Dual-currency reporting fields (`amount_base_usd` + `amount_display_local`) rather than mutating base transaction records.
   - Read-only visual presentation conversions without mutating PostgreSQL records.
