# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes the previously reported CSRF gaps by enforcing token checks on bartender invite confirmation, order replays, and bar pause toggles, with the frontend now supplying the token for each action.【F:main.py†L4192-L4237】【F:main.py†L5300-L5323】【F:main.py†L6263-L6313】【F:static/js/orders.js†L330-L357】【F:static/js/bar-orders.js†L1-L22】【F:templates/bartender_confirm.html†L1-L15】

**Last reviewed:** 2025-06-15

## Outstanding Findings

1. **DOM XSS on all-bars filter chips.** The "All bars" page builds removable chips for the name, city, and category filters by concatenating the raw input value into `chip.innerHTML`. A malicious value such as `<img src=x onerror=alert(1)>` executes immediately when the chip renders, allowing session theft for any user that pastes or autocompletes attacker-controlled text. The vulnerability lives in `addChip` within `static/js/view-all.js`.  
   • **Impact:** Stored DOM XSS in the browser session.  
   • **Reproduction:** Navigate to `/bars`, type `<img src=x onerror=alert(1)>` in the "Bar name" filter, submit. The chip renders the payload and triggers JavaScript execution.【F:static/js/view-all.js†L236-L279】  
   • **Suggested Mitigation:** Populate chips with `textContent` (or equivalent DOM nodes) instead of string concatenation and ensure all interpolated values are escaped.

2. **Unvalidated `photo_url` on bar API enables stored XSS.** The `/api/bars` endpoint accepts arbitrary strings for `photo_url` and later renders them in `<img>` tags after only normalising HTTP schemes. Attackers with API access can submit a `data:image/svg+xml,<svg onload=alert(1)>` payload that executes for every visitor when the bar card renders.  
   • **Impact:** Persistent cross-site scripting affecting homepage, search, and detail pages.  
   • **Reproduction:** Authenticate as a super admin, POST to `/api/bars` with `photo_url` set to a JavaScript-bearing SVG data URI, then load `/` to observe execution. `make_absolute_url` passes the payload straight through to the template.【F:main.py†L3232-L3265】【F:main.py†L2842-L2855】【F:templates/home.html†L37-L55】  
   • **Suggested Mitigation:** Restrict bar image sources to vetted schemes (e.g. `https`) or force uploads through `save_product_image` before persisting.
