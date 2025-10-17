# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes the previously reported CSRF gaps by enforcing token checks on bartender invite confirmation, order replays, and bar pause toggles, with the frontend now supplying the token for each action.【F:main.py†L4192-L4237】【F:main.py†L5300-L5323】【F:main.py†L6263-L6313】【F:static/js/orders.js†L330-L357】【F:static/js/bar-orders.js†L1-L22】【F:templates/bartender_confirm.html†L1-L15】 The June follow-up also remediates the outstanding XSS issues by rendering filter chips with text nodes and constraining bar photo URLs to HTTPS or site-hosted uploads.【F:static/js/view-all.js†L266-L283】【F:main.py†L274-L291】【F:main.py†L3458-L3465】 Chart.js is now self-hosted within `static/js/vendor/` so the admin analytics dashboard no longer depends on an unsigned CDN asset, the Bootstrap Icons stylesheet ships from `/static` with matching fonts tracked in-repo so integrators can bundle them safely, Inter is bundled locally via `/static/css/vendor/inter.css` so pages no longer reach out to Google Fonts, and remote disposable email blocklists must be served over HTTPS before they are ingested.【F:templates/admin_analytics.html†L158-L164】【F:templates/layout.html†L22-L28】【F:static/css/vendor/bootstrap-icons.css†L1-L20】【F:static/css/vendor/inter.css†L1-L24】【F:static/fonts/README.md†L1-L53】【F:app/utils/disposable_email.py†L20-L59】【F:app/utils/disposable_email.py†L92-L102】

**Last reviewed:** 2025-06-15

## Outstanding Findings

### Leaflet assets served from unpkg without integrity protection
- **Location:** `templates/admin_edit_bar.html`, `templates/admin_new_bar.html`【F:templates/admin_edit_bar.html†L1-L7】【F:templates/admin_new_bar.html†L1-L5】【F:templates/admin_edit_bar.html†L149-L156】【F:templates/admin_new_bar.html†L128-L135】
- **Impact:** Both admin bar-management templates pull Leaflet’s CSS and JavaScript from `unpkg.com` with no SRI hashes. A malicious update or CDN compromise would let attackers execute arbitrary JavaScript in privileged admin sessions (bar owners and super admins) or inject hostile CSS that captures form inputs such as address and contact data.
- **Mitigation:** Vendor the Leaflet assets within `static/` and adjust the CSP to remove the `unpkg.com` allowance so only self-hosted resources are permitted.
