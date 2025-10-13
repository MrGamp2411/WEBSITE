# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository. Each issue includes an impact assessment and recommended mitigation steps.

## Findings

### 1. Unauthenticated product image upload (High)
The `/api/products/{product_id}/image` endpoint accepts uploaded files without verifying that the caller is an authenticated or authorised staff member. Any internet user can overwrite a product image for any product ID, which enables defacement, malicious content injection, or a storage-based denial of service (despite the 5 MB limit per upload).【F:main.py†L2374-L2398】

**Recommendation:** Restrict the endpoint to authenticated bar staff or administrators (e.g. by requiring a valid session and authorisation check before processing the upload). Additionally, persist files via an object store or trusted CDN instead of raw database blobs to simplify validation and scanning.

### 2. Hard-coded session secret (High)
The application configures `SessionMiddleware` with the literal secret value `"dev-secret"`. Anyone who can read the source can forge session cookies and impersonate arbitrary users (including super administrators), completely bypassing authentication controls.【F:main.py†L768-L774】

**Recommendation:** Load a strong, randomly generated secret from the environment (e.g. `SESSION_SECRET`) in production, rotate it periodically, and ensure deployments never fall back to a placeholder.

### 3. Unauthenticated WebSocket subscriptions (Medium)
WebSocket endpoints (`/ws/bar/{bar_id}/orders` and `/ws/user/{user_id}/orders`) accept the caller-provided identifiers at face value and do not confirm the user’s identity. Attackers can connect to another user’s channel to receive order updates or supply an arbitrary bar ID to monitor staff traffic.【F:main.py†L3423-L3439】【F:main.py†L780-L815】

**Recommendation:** Require an authenticated session when upgrading to WebSockets. Validate that the connected user owns the requested channel (matching `user_id` or associated bar) before registering the socket, and immediately terminate mismatches.

### 4. Unbounded notification attachments (Medium)
`/admin/notifications` accepts optional image and attachment uploads but reads the entire file into memory without enforcing size limits or validating content type. A malicious administrator (or an attacker with a stolen admin session) could exhaust server memory or store dangerous payloads served back to end users.【F:main.py†L6603-L6705】【F:main.py†L6824-L6851】

**Recommendation:** Enforce explicit size caps (e.g. `<10 MB`) before reading files, restrict accepted MIME types, and scan attachments for malware. Consider storing large files externally with signed download URLs to avoid keeping binary blobs in application memory.

## Next Steps
Prioritise remediation of the high-severity issues (unauthenticated file upload and hard-coded session secret), then address WebSocket authorisation gaps and attachment handling. After implementing fixes, schedule a follow-up security assessment and add automated tests to cover these regressions.
