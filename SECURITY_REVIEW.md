# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, and cart table selections are validated against the cart's bar before being persisted or used at checkout.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】

**Last reviewed:** 2025-05-24

## Outstanding Findings

None. Stored XSS in the staff dashboards and customer order history was eliminated by escaping all bar-provided values before rendering order cards, ensuring websocket payloads can no longer inject markup into the DOM.【F:static/js/orders.js†L1-L235】【F:static/js/orders.js†L236-L360】
