# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes the previously reported CSRF gaps by enforcing token checks on bartender invite confirmation, order replays, and bar pause toggles, with the frontend now supplying the token for each action.【F:main.py†L4192-L4237】【F:main.py†L5300-L5323】【F:main.py†L6263-L6313】【F:static/js/orders.js†L330-L357】【F:static/js/bar-orders.js†L1-L22】【F:templates/bartender_confirm.html†L1-L15】

**Last reviewed:** 2025-06-15

## Outstanding Findings

None. Bar user management now blocks privilege changes for super-admin and finance accounts, only lets bar admins adjust staff already assigned to their venue, and protects removal operations from affecting elevated users.【F:main.py†L6003-L6113】 Bar/category/product mutation routes validate authorisation before touching database records so unauthorised callers always receive the same redirect response, closing the enumeration window.【F:main.py†L8386-L8433】【F:main.py†L8861-L9080】 The product image API checks authentication before loading menu items, eliminating status code discrepancies for unauthenticated probes.【F:main.py†L3029-L3046】 The Wallee webhook enforces signatures unless verification is explicitly disabled for trusted hosts, rejecting unsigned payloads from other sources to prevent forged payments.【F:app/webhooks/wallee.py†L15-L55】
