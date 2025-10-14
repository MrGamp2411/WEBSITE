# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L772-L874】【F:static/js/app.js†L1-L88】

## Findings

### 1. Product image upload API bypasses re-encoding (High) — Mitigated
Earlier revisions allowed staff uploads to bypass server-side re-encoding,
enabling stored XSS via crafted SVG payloads. The API now routes every upload
through `process_image_upload`, which verifies the binary data with Pillow,
converts it into a safe format, and stores the sanitised bytes alongside the
detected MIME type before committing them to the database.【F:main.py†L125-L214】【F:main.py†L2618-L2649】
Product images rendered on bar detail pages therefore inherit the trusted MIME
type returned by the sanitisation pipeline.【F:templates/bar_detail.html†L9-L76】

### 2. Session cookie missing `Secure` attribute (Medium) — Mitigated
The session cookie was previously issued without the `Secure` flag, so
deployments reachable over HTTPS but also serving occasional HTTP traffic (for
example via misconfigured reverse proxies) risked leaking session identifiers
over unencrypted connections. Middleware configuration now infers the correct
setting from the `SESSION_COOKIE_SECURE` toggle or the `BASE_URL` scheme,
automatically enabling `Secure` cookies whenever the site runs on HTTPS while
still supporting HTTP-only local development workflows.【F:main.py†L1003-L1016】

### 3. Unauthenticated disposable-email telemetry endpoint (Low) — Mitigated
The `/internal/disposable-domains/stats` route was exposed without
authentication and revealed operational metadata such as the number of cached
disposable domains and the timestamp of the last refresh. While this did not
leak customer data directly, it provided reconnaissance value to attackers
probing anti-abuse controls.【F:app/utils/disposable_email.py†L118-L126】

**Mitigation:** Access now requires a logged-in super admin, and the handler
responds with `404` unless the `DISPOSABLE_STATS_ENABLED` feature flag is
explicitly enabled. This keeps diagnostics off the public surface in
production environments.【F:main.py†L54-L63】【F:main.py†L4516-L4524】


## Next Steps
Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments.
Ensure deployment manifests explicitly set `SESSION_COOKIE_SECURE=true` (or advertise an HTTPS `BASE_URL`) so the runtime picks
up the secure-cookie behaviour, and schedule periodic reviews of newly exposed endpoints before release.
