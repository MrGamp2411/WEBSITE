# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, cart table selections are validated against the cart's bar before being persisted or used at checkout, authenticated product image downloads now enforce bar-level access controls, webhook signature verification can no longer be disabled in production, and every response includes hardened browser security headers.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】【F:main.py†L1209-L1252】【F:app/webhooks/wallee.py†L1-L47】

**Last reviewed:** 2025-06-09

## Outstanding Findings

### Missing CSRF validation on bar management forms

* **Description:** Multiple bar management POST handlers accept form submissions without calling `enforce_csrf`, and the corresponding templates omit the hidden `csrf_token` field. For example, the product creation, update, delete, and translation endpoints under `/bar/{bar_id}/categories/{category_id}/products/...` process form data directly after `await request.form()` with no CSRF verification, and the rendered forms have no token inputs. The new-category flow under `/bar/{bar_id}/categories/new` shows the same pattern.【F:main.py†L7987-L8069】【F:main.py†L8244-L8459】【F:main.py†L8536-L8779】【F:templates/bar_new_category.html†L18-L51】【F:templates/bar_category_products.html†L34-L52】【F:templates/bar_edit_product.html†L18-L47】【F:templates/bar_edit_product_name.html†L14-L24】【F:templates/bar_edit_product_description.html†L16-L26】
* **Impact:** A forged same-origin request (for example, triggered from a compromised subresource or future XSS gadget) can create, edit, or delete bar catalogue data without surfacing the "CSRF token missing" error other hardened forms return. The application currently trusts only the `Origin`/`Referer` headers for these flows, so any bypass of that check would let an attacker manipulate menu content or remove products on behalf of an authenticated bar administrator.
* **Recommended Mitigation:** Render `csrf_token` hidden inputs in all affected templates and invoke `await enforce_csrf(request)` (or otherwise require a valid CSRF token) in each corresponding POST handler before reading form data, matching the pattern used by other customer and admin forms.
