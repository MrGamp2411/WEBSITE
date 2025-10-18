# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes the previously reported CSRF gaps by enforcing token checks on bartender invite confirmation, order replays, and bar pause toggles, with the frontend now supplying the token for each action.【F:main.py†L4192-L4237】【F:main.py†L5300-L5323】【F:main.py†L6263-L6313】【F:static/js/orders.js†L330-L357】【F:static/js/bar-orders.js†L1-L22】【F:templates/bartender_confirm.html†L1-L15】 The June follow-up also remediates the outstanding XSS issues by rendering filter chips with text nodes and constraining bar photo URLs to HTTPS or site-hosted uploads.【F:static/js/view-all.js†L266-L283】【F:main.py†L274-L291】【F:main.py†L3458-L3465】

Chart.js is now self-hosted within `static/js/vendor/` so the admin analytics dashboard no longer depends on an unsigned CDN asset, the Bootstrap Icons stylesheet ships from `/static` with matching fonts tracked in-repo so integrators can bundle them safely, Inter is bundled locally via `/static/css/vendor/inter.css` so pages no longer reach out to Google Fonts, remote disposable email blocklists must be served over HTTPS before they are ingested, and Leaflet 1.9.4 now ships from `/static` with the CSP tightened to remove the `unpkg.com` allowance.【F:templates/admin_analytics.html†L158-L164】【F:templates/layout.html†L22-L28】【F:static/css/vendor/bootstrap-icons.css†L1-L20】【F:static/css/vendor/inter.css†L1-L24】【F:static/fonts/README.md†L1-L53】【F:app/utils/disposable_email.py†L20-L59】【F:app/utils/disposable_email.py†L92-L102】【F:templates/admin_edit_bar.html†L1-L18】【F:templates/admin_new_bar.html†L1-L18】【F:main.py†L1019-L1050】【F:static/css/vendor/leaflet/leaflet.css†L1-L120】

**Last reviewed:** 2025-06-16

## Outstanding Findings

### 1. Unauthenticated top-up initiation service (High)
- **Component:** `node-topup/src/server.ts`
- **Issue:** The Express microservice exposes `POST /api/topup/init` without any
  authentication, origin validation, or rate limiting. Any unauthenticated
  caller can create Wallee payment sessions on behalf of the platform and
  receive the hosted payment page URL. 【F:node-topup/src/server.ts†L1-L41】
- **Impact:** Attackers can generate unlimited real payment attempts, which can
  trigger unwanted charges against the merchant account, flood operations with
  bogus transactions, or be weaponised for phishing by abusing the legitimate
  SiplyGo payment page.
- **Recommendation:** Require the FastAPI backend to front this endpoint instead
  of exposing it publicly. At minimum enforce session authentication, CSRF
  protection, and strict rate limiting before forwarding requests to Wallee.

### 2. Default host allow-list permits host header spoofing (Medium)
- **Component:** `main.py`
- **Issue:** Even after `BASE_URL` is configured, the computed
  `TRUSTED_HOSTS` set retains the development defaults (`localhost`, `127.0.0.1`,
  `testserver`). `HostValidationMiddleware` therefore accepts requests that spoof
  those hostnames. 【F:main.py†L115-L162】【F:main.py†L189-L207】
- **Impact:** Host-header–driven features (absolute URL generation, link
  building in APIs, caches, or downstream proxies) can be forced to emit
  `https://localhost/...` style links, opening the door to cache poisoning and
  open-redirect style abuse if `BASE_URL` is ever omitted or mis-set.
- **Recommendation:** Remove the development hosts from the allow-list when a
  public origin is configured, or require operators to explicitly enumerate the
  full production host list via `ALLOWED_HOSTS`.

### 3. Content Security Policy still trusts external CDNs (Medium)
- **Component:** `main.py`
- **Issue:** `SecurityHeadersMiddleware` keeps
  `https://cdn.jsdelivr.net`, `https://fonts.googleapis.com`, and
  `https://fonts.gstatic.com` in the CSP allow-list despite self-hosting the
  corresponding assets. 【F:main.py†L1036-L1070】
- **Impact:** If an attacker compromises any of those third-party CDNs they can
  inject script, style, or font resources into the app despite the local asset
  mirror, undermining the CSP hardening.
- **Recommendation:** Drop the unused third-party origins from the CSP and rely
  solely on self-hosted assets (or re-introduce them only with Subresource
  Integrity checks).

### 4. Webhook signature can be disabled with weak IP checks (Medium)
- **Component:** `app/webhooks/wallee.py`
- **Issue:** Setting `WALLEE_VERIFY_SIGNATURE=false` allows unsigned requests as
  long as the client IP matches the `WALLEE_TRUSTED_IPS` list, which defaults to
  `127.0.0.1`, `::1`, `localhost`, and `testclient`. In proxy deployments the
  FastAPI app often sees the reverse proxy's address (e.g. `127.0.0.1`), so any
  insider or compromised service on the same host can forge wallet credits or
  order fulfilment events. 【F:app/webhooks/wallee.py†L18-L76】
- **Impact:** Forged webhooks can mark orders as paid or credit user wallets
  without real payments, enabling financial fraud.
- **Recommendation:** Remove the ability to disable signature verification in
  production or require mutual TLS/stronger network segmentation before
  honouring unsigned callbacks. Also narrow the trusted IP list to concrete
  payment-provider ranges.
