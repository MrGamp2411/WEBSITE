# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L772-L874】【F:static/js/app.js†L1-L99】

**Last reviewed:** 2025-05-15

## Findings

### Stored XSS via mini-cart rendering
- **Impact:** High – Bar admins can embed arbitrary HTML/JS into product names that later render inside the customer mini-cart without escaping, leading to stored cross-site scripting for any shopper viewing their cart. 【F:static/js/app.js†L683-L692】【F:main.py†L3510-L3519】【F:main.py†L7643-L7718】
- **Details:** `updateMiniCart` builds list markup with ``innerHTML`` and injects `i.name` values coming straight from the database. Product creation accepts and stores raw strings, so malicious markup persists and executes in customer sessions.
- **Mitigation:** Escape or text-node render cart item fields (e.g. via `textContent`) and add server-side validation stripping HTML from names/descriptions.

### CSRF via GET `/cart/select_table`
- **Impact:** Medium – The route mutates the active cart via a GET request which the CSRF middleware explicitly excludes, enabling cross-site attackers to force customers to reassign their table before checkout. 【F:main.py†L104-L106】【F:main.py†L830-L874】【F:main.py†L3524-L3536】
- **Details:** Visiting `/cart/select_table?table_id=<id>` updates the stored cart. Because GET is treated as a safe method, CSRF protections never run, so a crafted link can silently alter live orders.
- **Mitigation:** Change the endpoint to POST (or another non-safe verb) so the CSRF middleware enforces tokens, or add explicit verification before mutating session state.

## Next Steps
Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments.
Ensure deployment manifests explicitly set `SESSION_COOKIE_SECURE=true` (or advertise an HTTPS `BASE_URL`) so the runtime picks
up the secure-cookie behaviour, and schedule periodic reviews of newly exposed endpoints before release.
