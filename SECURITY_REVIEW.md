# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, cart table selections are validated against the cart's bar before being persisted or used at checkout, authenticated product image downloads now enforce bar-level access controls, webhook signature verification can no longer be disabled in production, and every response includes hardened browser security headers.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】【F:main.py†L1209-L1252】【F:app/webhooks/wallee.py†L1-L47】

**Last reviewed:** 2025-06-08

## Outstanding Findings

- None. All interactive forms now require a session CSRF token, with
  `enforce_csrf` invoked across authentication, account management, cart, and
  administrative POST routes, and templates embedding the token in each form
  submission. 【F:main.py†L3877-L3996】【F:main.py†L4579-L5192】【F:main.py†L5568-L7816】【F:templates/login.html†L11-L25】【F:templates/profile.html†L12-L63】
