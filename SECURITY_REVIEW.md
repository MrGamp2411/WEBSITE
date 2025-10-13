# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository. Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks discovered in the current codebase.

## Findings

### 1. Missing CSRF protection on session-authenticated POST routes (High)
The application relies on cookie-based sessions and exposes many POST endpoints that mutate state (cart updates, checkout, admin actions, etc.), but none of these handlers enforce a CSRF token or other origin check. A logged-in user’s browser can therefore be coerced (via a malicious site) into submitting a cross-origin form that executes privileged actions on their behalf, such as placing orders or modifying admin settings.【F:main.py†L1754-L1760】【F:main.py†L3279-L3312】

**Recommendation:** Introduce CSRF defences for all state-changing requests that use cookie authentication. Common mitigations include synchroniser tokens embedded in forms, double-submit cookies combined with same-site checks, or enforcing the `Origin`/`Referer` headers for JSON endpoints. Ensure the CSRF mechanism covers both HTML form submissions and XHR/Fetch requests.

### 2. Product photo uploads allow active content (High)
When staff add or edit menu items, uploaded “photo” files are written to `/static/uploads/` with the original extension preserved and no MIME validation. This allows SVG or HTML payloads containing JavaScript to be served back to customers, and browsers will execute scripts embedded in SVGs even when loaded via `<img>`, enabling stored cross-site scripting against anyone viewing the menu.【F:main.py†L2296-L2321】【F:main.py†L7419-L7476】

**Recommendation:** Restrict uploads to safe image types (e.g., JPEG/PNG/WebP), validate the content matches the declared MIME type, and rewrite files with benign extensions. Alternatively, serve uploads from an isolated domain without session cookies, or process images (e.g., re-encode using Pillow) before storage to strip active content.

## Next Steps
Prioritise remediation of the high-severity issues above. After implementing fixes, perform a regression review (including automated tests) to ensure CSRF protections cover all session-backed POST routes and that file upload hardening cannot be bypassed by crafted payloads.
