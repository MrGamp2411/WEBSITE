# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L772-L874】【F:static/js/app.js†L1-L99】
The mini-cart now renders entries with text nodes only, and table selection is handled through a POST endpoint so the
CSRF middleware protects the mutation path.【F:static/js/app.js†L683-L715】【F:main.py†L3524-L3538】

**Last reviewed:** 2025-05-15

## Findings

### Stored XSS via bar names in cart overlays *(New)*
- **Impact:** A malicious bar owner can rename their venue to inject HTML/JS that is rendered without escaping inside the cart reminder and service-paused overlays. The templates mark the translation block as safe, so the injected markup executes for any customer who still has that bar in their cart or who visits while the bar is paused. This enables account takeover, credential theft, or payment redirection with a single bar-name change.
- **Evidence:** `render_template` passes the bar’s raw `name` into the `cart_bar_name` context, and the layout uses that value inside a `|safe` translation string, disabling escaping.【F:main.py†L2510-L2531】【F:templates/layout.html†L149-L167】
- **Mitigation:** Escape the interpolated bar name (e.g. use `|e` before `|safe`, or build the `<strong>` element separately) so translated HTML remains allowed while user data stays encoded. Add regression coverage around the overlay components.

### Notification deep links allow `javascript:` URIs *(New)*
- **Impact:** Super admins can craft notifications whose CTA links point to `javascript:` URLs. When recipients open the notification detail page and click the link, the browser executes attacker-controlled script in the user’s context, leading to stored XSS.
- **Evidence:** The notification sender stores the `link_url` verbatim on each notification record, and the detail template renders it directly in an `<a>` tag without scheme validation.【F:main.py†L7250-L7273】【F:templates/notification_detail.html†L6-L15】
- **Mitigation:** Restrict `link_url` to safe schemes (https/mailto/tel) server-side and refuse unsafe input. Also normalise links before rendering or omit them when validation fails.

## Next Steps
Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments. Ensure deployment manifests explicitly set `SESSION_COOKIE_SECURE=true` (or advertise an HTTPS `BASE_URL`) so the runtime picks up the secure-cookie behaviour, and schedule periodic reviews of newly exposed endpoints before release. Prioritise patching the stored-XSS vectors above before adding new marketing or notification features.
