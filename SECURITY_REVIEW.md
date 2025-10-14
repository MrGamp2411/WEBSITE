# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L762-L842】【F:static/js/app.js†L1-L88】

## Findings

### 1. Product image upload API bypasses re-encoding (High)
The JSON API that allows staff to upload product artwork still persists the raw bytes supplied by the client and trusts the
declared `Content-Type`. Any authenticated bar admin or bartender can therefore upload an SVG (or other active payload) that
will be stored verbatim and later served back with the attacker-controlled MIME type.【F:main.py†L2600-L2647】 Customer-facing
templates embed these images directly via `<img>` tags, so a malicious SVG will execute script in every visitor’s browser,
resulting in stored cross-site scripting across bar pages and admin dashboards.【F:templates/bar_detail.html†L80-L105】

**Recommendation:** Reuse the existing `process_image_upload` pipeline to verify and re-encode uploads before storage. Reject
non-binary image types (SVG/HTML), cap file sizes, and consider serving transformed assets from a distinct host without cookies
attached.

### 2. Unauthenticated disposable-email telemetry endpoint (Low) — Mitigated
The `/internal/disposable-domains/stats` route was exposed without authentication and revealed operational metadata such as the number of cached disposable domains and the timestamp of the last refresh. While this did not leak customer data directly, it provided reconnaissance value to attackers probing anti-abuse controls.【F:app/utils/disposable_email.py†L118-L126】

**Mitigation:** Access now requires a logged-in super admin, and the handler responds with `404` unless the `DISPOSABLE_STATS_ENABLED` feature flag is explicitly enabled. This keeps diagnostics off the public surface in production environments.【F:main.py†L54-L63】【F:main.py†L4516-L4524】

## Next Steps
Prioritise remediation of the high-severity issue above. After implementing fixes, perform a regression review (including
automated tests) to ensure the hardened upload flow cannot be bypassed and that diagnostic endpoints intended for operators are
not exposed publicly.
