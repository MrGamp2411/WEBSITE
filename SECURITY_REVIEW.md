# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, cart table selections are validated against the cart's bar before being persisted or used at checkout, authenticated product image downloads now enforce bar-level access controls, webhook signature verification can no longer be disabled in production, every response includes hardened browser security headers, and bar management forms now require CSRF tokens on both the client and server.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】【F:main.py†L1209-L1252】【F:app/webhooks/wallee.py†L1-L47】【F:main.py†L7983-L9054】【F:templates/bar_new_category.html†L18-L48】【F:templates/bar_manage_categories.html†L53-L77】【F:templates/bar_category_products.html†L56-L83】【F:templates/bar_new_product.html†L10-L26】【F:templates/bar_edit_product.html†L18-L45】【F:templates/bar_edit_product_name.html†L14-L30】【F:templates/bar_edit_product_description.html†L14-L30】【F:templates/bar_edit_category.html†L17-L33】【F:templates/bar_edit_category_name.html†L14-L30】【F:templates/bar_edit_category_description.html†L14-L30】

**Last reviewed:** 2025-06-10

## Outstanding Findings

None.
