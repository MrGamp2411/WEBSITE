# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, and cart table selections are validated against the cart's bar before being persisted or used at checkout.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】

**Last reviewed:** 2025-05-25

## Outstanding Findings

### Missing browser security headers
- **Impact:** The application does not emit standard hardening headers such as `Content-Security-Policy`, `X-Frame-Options`, or `X-Content-Type-Options`, leaving every page vulnerable to clickjacking and widening the blast radius of any future cross-site scripting issue. Because the FastAPI app only installs custom middleware, browsers receive the default permissive behaviour.【F:main.py†L1184-L1214】
- **Mitigation:** Add a security middleware that sets strict defaults (e.g. Starlette's `SecurityMiddleware` or a custom middleware emitting CSP, frame-ancestors `none`, referrer policy, and MIME sniffing protections) and document required overrides.

### Product image endpoint allows unauthorised access
- **Impact:** `/api/products/{product_id}/image` returns raw product photography without checking the caller's role. Anyone who can guess or enumerate product IDs can download assets, revealing unpublished menu items or seasonal promotions ahead of launch.【F:main.py†L2962-L2990】
- **Mitigation:** Require authentication and ensure the requester is associated with the bar that owns the product before returning the image, or move public assets to a CDN bucket with signed URLs.

### Webhook signature verification can be disabled by configuration
- **Impact:** Setting `WALLEE_VERIFY_SIGNATURE=false` skips signature checks entirely, so any actor who can reach `/webhooks/wallee` may forge payout confirmations and wallet credits. The code merely prints a warning and proceeds, offering no defence in depth if an environment variable is mis-set or tampered with.【F:app/webhooks/wallee.py†L19-L40】
- **Mitigation:** Remove the bypass in production builds or gate it behind an explicit development flag that is ignored when `ENV` is `production`. Consider failing closed when verification cannot run.
