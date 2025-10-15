# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository.
Each issue includes an impact assessment and recommended mitigation steps. The items below reflect the most pressing risks
discovered in the current codebase.

Recent changes introduced CSRF middleware plus front-end helpers that populate a `csrf_token` field automatically, which
mitigates the previously reported cross-site request forgery risk.【F:main.py†L772-L874】【F:static/js/app.js†L1-L99】 The
mini-cart now renders entries with text nodes only, and table selection is handled through a POST endpoint so the CSRF
middleware protects the mutation path.【F:static/js/app.js†L683-L715】【F:main.py†L3524-L3538】 Bar names rendered in cart
overlays are now escaped before being inserted into translated HTML, preventing stored XSS payloads from executing in the
customer cart or pause popups.【F:templates/layout.html†L156-L176】 Notification deep links are normalised server-side and
must use an approved scheme (HTTP(S), mailto, or tel). Unsafe values are rejected, and templates escape the resulting URLs
before rendering.【F:main.py†L97-L121】【F:main.py†L7228-L7263】【F:templates/notification_detail.html†L13-L16】【F:templates/admin_notification_view.html†L30-L34】
Super admin credentials are now required at startup, login throttling data is persisted per email and subnet, registration
returns a generic failure when an address already exists, and session cookies always demand an explicit secure
configuration before booting.【F:main.py†L1230-L1272】【F:main.py†L1927-L2068】【F:main.py†L4367-L4388】【F:main.py†L120-L140】

The latest review uncovered three high-risk issues detailed below.

**Last reviewed:** 2025-05-19

## Findings

### 1. Host header poisoning in absolute URL generation

Several flows derive absolute URLs directly from `request.base_url`, which is populated from the incoming `Host`
header. Attackers who can spoof the header (for example when requests traverse a misconfigured reverse proxy) can force
the application to emit third-party origins in checkout redirects and media URLs. This enables open redirects during
card payments and asset poisoning in rendered templates.【F:main.py†L2631-L2638】【F:main.py†L3742-L3783】
**Mitigation:** Resolve the public origin from trusted configuration (e.g. `BASE_URL`) and validate runtime `Host`
headers against an allow-list before reusing them in responses.

### 2. Spoofable client IP address handling

`get_request_ip` trusts the first value supplied in the `X-Forwarded-For` header without checking that the request
traversed a trusted proxy. Because login throttling, registration logging, and IP blocking use this helper, an attacker
can bypass lockouts or unban themselves simply by forging the header value.【F:main.py†L1952-L1959】【F:main.py†L4564-L4570】
**Mitigation:** Strip or ignore `X-Forwarded-For` unless the application is explicitly behind a trusted proxy that can
be validated (for example via `Forwarded` headers plus a configured allow-list), and fall back to `request.client.host`
for security controls.

### 3. Table selection lacks server-side bar validation

The cart workflow accepts arbitrary table identifiers without confirming that the table belongs to the bar associated
with the current cart. As a result, a malicious customer can submit an order for Bar A that references a table from Bar B,
leaking table metadata across tenants and confusing staff dashboards.【F:main.py†L3670-L3703】
**Mitigation:** When selecting a table and again during checkout, verify that the requested table exists and is linked to
the cart's bar before persisting it or placing the order.
