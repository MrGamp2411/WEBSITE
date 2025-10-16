# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, cart table selections are validated against the cart's bar before being persisted or used at checkout, authenticated product image downloads now enforce bar-level access controls, webhook signature verification can no longer be disabled in production, every response includes hardened browser security headers, and bar management forms now require CSRF tokens on both the client and server.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】【F:main.py†L1209-L1252】【F:app/webhooks/wallee.py†L1-L47】【F:main.py†L7983-L9054】【F:templates/bar_new_category.html†L18-L48】【F:templates/bar_manage_categories.html†L53-L77】【F:templates/bar_category_products.html†L56-L83】【F:templates/bar_new_product.html†L10-L26】【F:templates/bar_edit_product.html†L18-L45】【F:templates/bar_edit_product_name.html†L14-L30】【F:templates/bar_edit_product_description.html†L14-L30】【F:templates/bar_edit_category.html†L17-L33】【F:templates/bar_edit_category_name.html†L14-L30】【F:templates/bar_edit_category_description.html†L14-L30】

**Last reviewed:** 2025-06-10

## Outstanding Findings

- **GET invite confirmation lacks CSRF** – `/confirm_bartender` updates the logged-in
  user’s role and removes their pending invite purely through a GET request with a
  `bar_id` query parameter, so a crafted image tag or link can auto-accept a
  bartender invite without the user’s consent. Mitigation: switch the route to a
  POST that requires `await enforce_csrf` and include the CSRF token in the
  confirmation UI.【F:main.py†L6261-L6280】
- **Reorder endpoint skips explicit CSRF validation** –
  `/orders/{order_id}/reorder` mutates the session cart but never calls
  `await enforce_csrf`, relying only on the middleware’s origin heuristics.
  Attackers who can trigger same-origin requests (e.g., via compromised static
  assets) can silently repopulate a victim’s cart. Mitigation: add
  `await enforce_csrf(request)` before reading the request body and ensure the
  reorder button includes the CSRF token.【F:main.py†L4192-L4223】
- **Bar pause toggle missing CSRF token enforcement** – the admin/bartender API at
  `/dashboard/bar/{bar_id}/toggle_pause` updates bar availability based on JSON
  input but never enforces a CSRF token, so the service state can be flipped with a
  forged same-origin request. Mitigation: require `await enforce_csrf` and send the
  token from `bar-orders.js` when toggling the pause switch.【F:main.py†L5299-L5319】
