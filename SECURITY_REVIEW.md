# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, and cart table selections are validated against the cart's bar before being persisted or used at checkout.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】

**Last reviewed:** 2025-05-25

## Outstanding Findings

None. Logout now requires a CSRF-protected POST flow, notification read status updates are handled via an authenticated POST endpoint, and the "recently viewed" carousel is populated through a CSRF-validated POST that the bar detail page triggers client-side.【F:main.py†L5054-L5077】【F:templates/layout.html†L33-L44】【F:main.py†L7700-L7745】【F:static/js/app.js†L79-L97】【F:main.py†L3626-L3652】【F:static/js/bar-detail.js†L1-L24】
