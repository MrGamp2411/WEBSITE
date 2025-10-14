# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L772-L874】【F:static/js/app.js†L1-L99】

**Last reviewed:** 2025-05-15

## Findings

### Stored XSS in live order dashboards via unchecked order notes
- **Impact:** Customer-supplied order notes are written to the database without
  sanitisation and later injected directly into the bartender/admin order
  dashboards through `innerHTML`. A malicious customer can submit HTML/JS in the
  notes field during checkout; when staff review the order the script executes
  in their browser, enabling session hijacking or privileged actions such as
  marking orders complete or issuing refunds.
- **Evidence:** The checkout handler persists raw `notes` form input in the
  `Order` model, and the live order rendering logic interpolates `order.notes`
  straight into a template string.【F:main.py†L3544-L3694】【F:static/js/orders.js†L90-L146】
- **Mitigation:** Escape or sanitise order notes before rendering in
  `orders.js` (e.g. create text nodes instead of assigning `innerHTML`) or store
  an HTML-escaped version server-side. Add regression tests to ensure only plain
  text appears in the dashboard output.


## Next Steps
Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments.
Ensure deployment manifests explicitly set `SESSION_COOKIE_SECURE=true` (or advertise an HTTPS `BASE_URL`) so the runtime picks
up the secure-cookie behaviour, and schedule periodic reviews of newly exposed endpoints before release.
