# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, and cart table selections are validated against the cart's bar before being persisted or used at checkout.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】

**Last reviewed:** 2025-05-21

## Outstanding Findings

1. **Unauthenticated login coordinates trigger unhandled exception**  
   - **Impact:** An attacker can send non-numeric `latitude` or `longitude` fields to the `/login` form, causing `float()` to raise `ValueError` and return a 500 response. This enables low-effort denial-of-service attempts against the login endpoint.  
   - **Evidence:** `lat = float(latitude) if latitude else None` and `lon = float(longitude) if longitude else None` convert untrusted form fields without validation or error handling.【F:main.py†L4694-L4697】  
   - **Mitigation:** Wrap the conversions in `try/except` (or use `pydantic` validation) and reject invalid coordinates with a user-facing error instead of letting the exception propagate.

2. **Order status API leaks order existence to unauthorized users**  
   - **Impact:** Any authenticated user can probe `/api/orders/{order_id}/status` and distinguish valid order IDs via the 404 vs. 403 responses, aiding enumeration of other users’ orders.  
   - **Evidence:** The handler fetches the order and raises a 404 before verifying the requester’s permissions, but returns 403 when the order exists yet the user lacks rights.【F:main.py†L4144-L4177】  
   - **Mitigation:** Authorize the user *before* disclosing whether the order exists (e.g., return a generic 403/404 for unauthorized callers or merge the checks).

3. **Bar product edit pages reveal bar/product IDs through 404 timing**  
   - **Impact:** Requests to `/bar/{bar_id}/categories/{category_id}/products/{product_id}/edit` raise 404 errors for unknown bars/products *before* permissions are evaluated, but redirect unauthorized users when resources exist. Attackers can map valid IDs for bars they do not manage.  
   - **Evidence:** The route loads the bar, category, and product and raises 404s prior to verifying `user.is_super_admin`/bar ownership, only enforcing authorization afterwards.【F:main.py†L8072-L8116】  
   - **Mitigation:** Check authorization immediately after retrieving the current user (returning a uniform 403/404), or defer the detailed lookups until after permission is confirmed.
