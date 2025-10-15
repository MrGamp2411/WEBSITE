# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes all previously reported findings: absolute URLs now rely on a configured public origin and requests with unrecognised `Host` headers are rejected, `X-Forwarded-For` is honoured only for connections coming from trusted proxies, and cart table selections are validated against the cart's bar before being persisted or used at checkout.【F:main.py†L111-L205】【F:main.py†L2062-L2085】【F:main.py†L3797-L3844】

**Last reviewed:** 2025-05-21

## Outstanding Findings

None. The May 2025 findings were remediated by validating optional login coordinates before parsing,【F:main.py†L4720-L4732】 returning uniform 404 responses from the order status API when callers lack access,【F:main.py†L4156-L4177】 and enforcing authorisation checks ahead of bar/product lookups on edit and delete routes to avoid ID probing.【F:main.py†L8070-L8107】
