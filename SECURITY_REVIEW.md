# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes the previously reported CSRF gaps by enforcing token checks on bartender invite confirmation, order replays, and bar pause toggles, with the frontend now supplying the token for each action.【F:main.py†L4192-L4237】【F:main.py†L5300-L5323】【F:main.py†L6263-L6313】【F:static/js/orders.js†L330-L357】【F:static/js/bar-orders.js†L1-L22】【F:templates/bartender_confirm.html†L1-L15】 The June follow-up also remediates the outstanding XSS issues by rendering filter chips with text nodes and constraining bar photo URLs to HTTPS or site-hosted uploads.【F:static/js/view-all.js†L266-L283】【F:main.py†L274-L291】【F:main.py†L3458-L3465】

**Last reviewed:** 2025-06-15

## Outstanding Findings

No outstanding issues are currently tracked.
