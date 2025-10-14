# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L772-L874】【F:static/js/app.js†L1-L99】
The mini-cart now renders entries with text nodes only, and table selection is handled through a POST endpoint so the
CSRF middleware protects the mutation path.【F:static/js/app.js†L683-L715】【F:main.py†L3524-L3538】
Bar names rendered in cart overlays are now escaped before being inserted into translated HTML, preventing stored XSS
payloads from executing in the customer cart or pause popups.【F:templates/layout.html†L156-L176】
Notification deep links are normalised server-side and must use an approved scheme (HTTP(S), mailto, or tel). Unsafe
values are rejected, and templates escape the resulting URLs before rendering.【F:main.py†L97-L121】【F:main.py†L7228-L7263】【F:templates/notification_detail.html†L13-L16】【F:templates/admin_notification_view.html†L30-L34】

**Last reviewed:** 2025-05-15

## Findings

No outstanding findings remain at this time.

## Next Steps
Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments. Ensure deployment manifests explicitly set `SESSION_COOKIE_SECURE=true` (or advertise an HTTPS `BASE_URL`) so the runtime picks up the secure-cookie behaviour, and schedule periodic reviews of newly exposed endpoints before release. Prioritise patching the stored-XSS vectors above before adding new marketing or notification features.
