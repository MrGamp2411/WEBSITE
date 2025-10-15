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
Super admin credentials are now required at startup, login throttling data is persisted per email and subnet, registration returns a generic failure when an address already exists, and session cookies always demand an explicit secure configuration before booting.【F:main.py†L1230-L1272】【F:main.py†L1927-L2068】【F:main.py†L4367-L4388】【F:main.py†L120-L140】

**Last reviewed:** 2025-05-17

## Findings

No outstanding findings. Recent remediation work addressed the previously logged risks by hardening credential seeding, login throttling, registration messaging, and session cookie configuration. Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments, and schedule periodic reviews of newly exposed endpoints before release.
