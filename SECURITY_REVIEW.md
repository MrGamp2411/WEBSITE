# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, cart table selections are validated against the cart's bar before being persisted or used at checkout, authenticated product image downloads now enforce bar-level access controls, webhook signature verification can no longer be disabled in production, and every response includes hardened browser security headers.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】【F:main.py†L1209-L1252】【F:app/webhooks/wallee.py†L1-L47】

**Last reviewed:** 2025-06-08

## Outstanding Findings

- **Wallet top-up API leaks upstream error details (medium).** The
  `POST /api/topup/init` handler reflects raw exception strings from the Wallee
  SDK back to the caller (for example `"Wallee create error: {e}"` and
  `"Wallee payment page error: {e}"`). An attacker can deliberately trigger
  failures and harvest gateway responses that may expose identifiers, request
  metadata, or other sensitive information that helps with further abuse. Replace
  these responses with generic error messages and log the detailed exception on
  the server instead.【F:main.py†L4441-L4563】
- **Malformed Wallee webhooks acknowledged as successful (medium).** When the
  webhook payload is missing an `entityId`/`id` or cannot be parsed, the handler
  returns `{"ok": true}` with HTTP 200. In environments where signature
  verification is disabled (e.g. `WALLEE_VERIFY_SIGNATURE=false`), an unauthenticated
  actor can repeatedly post junk payloads to exhaust webhook retries and prevent
  legitimate completion events from crediting wallets. The endpoint should return
  an error for invalid payloads and keep verification permanently enabled in
  production.【F:app/webhooks/wallee.py†L22-L54】
