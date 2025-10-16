# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes the previously reported CSRF gaps by enforcing token checks on bartender invite confirmation, order replays, and bar pause toggles, with the frontend now supplying the token for each action.【F:main.py†L4192-L4237】【F:main.py†L5300-L5323】【F:main.py†L6263-L6313】【F:static/js/orders.js†L330-L357】【F:static/js/bar-orders.js†L1-L22】【F:templates/bartender_confirm.html†L1-L15】

**Last reviewed:** 2025-06-11

## Outstanding Findings

### Bar admins can strip super-admin privileges
*Impact:* A bar administrator can demote any account, including super administrators, by using the “Manage Bar Users” form. The handler trusts the submitted email and unconditionally overwrites the target’s `role`, so a malicious bar admin can remove global oversight or assign a super admin to their venue with reduced permissions.【F:main.py†L6003-L6069】

*Recommendation:* Refuse to change roles for super-admin accounts (and other elevated roles) inside this endpoint and require a super admin session for privilege changes. Only allow bar admins to manage users already scoped to their venue.

### Bar management POST routes leak resource existence
*Impact:* Several POST handlers in the bar/category/product management flow load database objects and raise `404` before verifying the caller’s privileges. When an attacker hits these endpoints without access, existing IDs return a redirect while invalid IDs return `404`, enabling enumeration of bar, category, and product identifiers and revealing which venues exist in the system.【F:main.py†L8384-L8421】【F:main.py†L8851-L8866】【F:main.py†L8963-L8978】

*Recommendation:* Check authorisation before fetching and validating the target records, and return the same generic response for unauthorised callers regardless of whether the ID exists.

### Product image API exposes menu presence
*Impact:* `GET /api/products/{product_id}/image` answers `401` for existing menu items when the caller lacks a session but `404` when the ID is invalid. This difference allows unauthenticated probing of product inventory for any bar.【F:main.py†L3029-L3050】

*Recommendation:* Perform the authorisation check before loading the product or always return the same error for unauthenticated requests.

### Wallee webhook signature can be disabled
*Impact:* The Wallee webhook honours the `WALLEE_VERIFY_SIGNATURE` flag whenever `ENV` is not `production` (the default). If that flag is set to `false`, signature checks are skipped entirely, letting an attacker forge payment or top-up events.【F:app/webhooks/wallee.py†L19-L42】

*Recommendation:* Enforce signature validation regardless of environment, or at minimum guard the webhook by additional controls (e.g. trusted source IP allow-lists) when verification is disabled.
