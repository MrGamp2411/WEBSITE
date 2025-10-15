# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, cart table selections are validated against the cart's bar before being persisted or used at checkout, authenticated product image downloads now enforce bar-level access controls, webhook signature verification can no longer be disabled in production, and every response includes hardened browser security headers.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】【F:main.py†L1209-L1252】【F:app/webhooks/wallee.py†L1-L47】

**Last reviewed:** 2025-05-25

## Outstanding Findings

- **Critical – Authentication forms lack CSRF protection.** The primary login
  handler and both registration steps accept cross-site form submissions or
  scripted requests without ever calling `enforce_csrf`, so an attacker can
  silently sign a victim up or attempt logins while their browser forwards
  authentication cookies. 【F:main.py†L4801-L4869】【F:main.py†L4578-L4660】【F:main.py†L4677-L4759】
- **High – Account management flows are CSRF-exposed.** Profile edits and
  password changes process POST bodies directly with no CSRF validation,
  letting a malicious site update a signed-in user’s account details or reset
  their password. 【F:main.py†L4996-L5054】【F:main.py†L5136-L5163】
- **High – Cart and checkout endpoints miss CSRF enforcement.** Actions such as
  `POST /cart/update`, `POST /cart/select_table`, and `POST /cart/checkout`
  mutate the active order purely on session cookies, enabling forced orders or
  table selections via cross-site requests. 【F:main.py†L3877-L3931】【F:main.py†L3934-L3996】
- **Critical – Admin management POST routes omit CSRF checks.** Administrative
  submissions (for example `POST /admin/bars/new` and `POST /admin/users/{id}/delete`)
  never verify a CSRF token, so compromising a super admin’s browser lets an
  attacker create or delete records through a single lure page. 【F:main.py†L5567-L5594】【F:main.py†L7213-L7237】
