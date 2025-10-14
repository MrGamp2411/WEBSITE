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

**Last reviewed:** 2025-05-16

## Findings

### Default super admin credentials
**Impact:** When the environment does not override `ADMIN_EMAIL` and `ADMIN_PASSWORD`, the application seeds a SuperAdmin account with the publicly documented credentials `admin@example.com` / `ChangeMe!123`. Anyone who can reach the login page can take over the platform by signing in with these defaults.【F:main.py†L1210-L1232】

**Mitigation:** Fail startup unless secure administrator credentials are provided via environment variables, or generate a random password that must be retrieved from deployment secrets.

### Registration reveals whether an email exists
**Impact:** The `/register` handler returns a distinct "Email already taken" error when an address is present in the database, allowing unauthenticated attackers to enumerate customer accounts.【F:main.py†L4203-L4238】

**Mitigation:** Return a generic response for all registration failures and defer specific feedback to a verified channel (e.g., confirmation email).

### Login throttling can be bypassed
**Impact:** Login attempts are tracked only per email address in an in-memory dictionary. Attackers can rotate through many usernames or restart distributed attacks without hitting a durable lockout, leaving accounts exposed to brute-force guessing despite the exponential sleep after five tries.【F:main.py†L1924-L1927】【F:main.py†L4437-L4440】

**Mitigation:** Persist counters and rate-limit by client network identifiers (IP / subnet) in addition to usernames, with hard caps that trigger temporary lockouts.

### Session cookies may be issued without the `Secure` flag
**Impact:** `should_use_secure_session_cookie` only enables the `Secure` attribute when `BASE_URL` is HTTPS or `SESSION_COOKIE_SECURE` is explicitly set. In the default configuration both are empty, so a production deployment that forgets to set these values would transmit session cookies over HTTP, enabling theft on shared networks.【F:main.py†L117-L126】【F:main.py†L1036-L1047】

**Mitigation:** Force `https_only=True` by default and fail fast if the application is started without an explicit decision about secure cookies.

## Next Steps
Continue regression-testing the hardened upload pipeline and session middleware across staging and production environments. Ensure deployment manifests explicitly set `SESSION_COOKIE_SECURE=true` (or advertise an HTTPS `BASE_URL`) so the runtime picks up the secure-cookie behaviour, and schedule periodic reviews of newly exposed endpoints before release. Prioritise patching the stored-XSS vectors above before adding new marketing or notification features.
