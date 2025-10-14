# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L772-L874】【F:static/js/app.js†L1-L88】

## Findings

### Stored XSS in live order dashboards via unchecked order notes
- **Impact:** Customer-supplied order notes are written to the database without
  sanitisation and later injected directly into the bartender/admin order
  dashboards through `innerHTML`. An attacker can submit HTML/JS in the notes
  field during checkout, which will execute for staff reviewing live orders,
  enabling session hijacking or pivoting into privileged admin actions.
- **Evidence:** The checkout handler persists raw `notes` from the form payload
  into the `Order` record, while the real-time order rendering script inserts
  `order.notes` into the DOM without escaping.【F:main.py†L3527-L3597】【F:static/js/orders.js†L94-L146】
- **Mitigation:** Escape or sanitise order notes before rendering in
  `orders.js` (e.g. convert text to DOM text nodes) or store an HTML-escaped
  version server-side. Add regression tests to ensure only plain text appears
  in the dashboard.


## Next Steps
Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments.
Ensure deployment manifests explicitly set `SESSION_COOKIE_SECURE=true` (or advertise an HTTPS `BASE_URL`) so the runtime picks
up the secure-cookie behaviour, and schedule periodic reviews of newly exposed endpoints before release.
