# Security Review

## Overview
This document captures potential vulnerabilities observed during a manual review of the FastAPI application in this repository. Each issue includes an impact assessment and recommended mitigation steps. Previously reported high-risk flaws around product image uploads, the session secret, WebSocket authorisation, and notification attachments have been remediated; the findings below reflect the current outstanding risks.

## Findings

### 1. Unauthenticated bar creation (High)
The public REST API exposes `POST /api/bars` without any authentication or authorisation. Any internet user can create or mutate bar records, polluting production data, overriding legitimate listings, or abusing the platform to host fraudulent content.【F:main.py†L2780-L2802】

**Recommendation:** Require an authenticated super administrator session (or an equivalent admin token) before allowing bar creation. Reject anonymous requests and log failed attempts for monitoring.

### 2. Unauthenticated payout scheduling (High)
`POST /api/payouts/run` similarly omits permission checks. An attacker can fabricate payouts for arbitrary bars, manipulating accounting records and potentially triggering downstream payment workflows or reports that rely on payout status.【F:main.py†L2864-L2890】

**Recommendation:** Restrict this endpoint to authorised finance or super admin users and validate the actor from the current session rather than accepting an arbitrary `actor_user_id` payload. Add rate limiting and audit logging for failed attempts.

### 3. Anonymous order submission (High)
`POST /api/orders` lets unauthenticated callers place orders for any bar. Although no payment is collected, the endpoint inserts fully-fledged orders into the database, generating live work for bartenders and triggering websocket notifications. Attackers can exploit this to flood venues with bogus orders and disrupt operations.【F:main.py†L2805-L2861】

**Recommendation:** Require a logged-in customer before creating an order, associating the order with the caller’s user ID. Apply server-side validation (e.g. CAPTCHA, rate limits) to deter automated abuse and ensure payment or wallet balance is verified prior to confirming the order.

## Next Steps
Prioritise remediation of the three high-severity issues above. After implementing fixes, perform a regression review (including automated tests) to ensure admin-only APIs enforce authentication and that order placement validates the customer identity and payment state.
