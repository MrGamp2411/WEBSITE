# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, and cart table selections are validated against the cart's bar before being persisted or used at checkout.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】

**Last reviewed:** 2025-05-24

## Outstanding Findings

### Stored XSS in staff order dashboards
- **Impact:** A malicious bar admin can inject JavaScript into bartender and bar admin dashboards. The injected script executes in the context of privileged staff accounts viewing `/dashboard/bar/{bar_id}/orders`, enabling credential theft or arbitrary actions via the staff session.
- **Details:** The live order widgets build HTML with template literals that interpolate `order.bar_name`, `order.table_name`, and `order.items[*].menu_item_name` directly into `innerHTML` without escaping.【F:static/js/orders.js†L137-L160】 Those fields originate from database columns that bar operators fully control via bar and menu editing flows.【F:models.py†L80-L152】【F:main.py†L1300-L1329】 Because the websocket payload includes the raw values, any HTML in those fields is rendered and executed.
- **Mitigation:** Escape or text-encode all dynamic values before injecting them into the DOM (for example, by using `textContent` and building nodes manually) so markup provided by bar data cannot execute.

### Stored XSS in customer order history
- **Impact:** Malicious bar content also executes for customers browsing their order history at `/orders`, allowing theft of session cookies, redirection to phishing pages, or unauthorized wallet actions in the victim’s browser.
- **Details:** The customer-facing renderer in `initUser` repeats the unsafe interpolation pattern, placing `order.bar_name`, `order.table_name`, and `order.items[*].menu_item_name` inside `innerHTML` without sanitisation.【F:static/js/orders.js†L257-L279】 The data is sourced from the same bar-controlled database columns provided through the order websocket payload.【F:models.py†L80-L316】【F:main.py†L1300-L1329】
- **Mitigation:** Replace the string concatenation with DOM APIs or apply rigorous escaping before insertion to ensure customer views treat bar-managed content as plain text.
