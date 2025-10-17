# Security Review

## Overview
This document captures outstanding security issues discovered during manual reviews of the FastAPI application. The current release closes the previously reported CSRF gaps by enforcing token checks on bartender invite confirmation, order replays, and bar pause toggles, with the frontend now supplying the token for each action.【F:main.py†L4192-L4237】【F:main.py†L5300-L5323】【F:main.py†L6263-L6313】【F:static/js/orders.js†L330-L357】【F:static/js/bar-orders.js†L1-L22】【F:templates/bartender_confirm.html†L1-L15】 The June follow-up also remediates the outstanding XSS issues by rendering filter chips with text nodes and constraining bar photo URLs to HTTPS or site-hosted uploads.【F:static/js/view-all.js†L266-L283】【F:main.py†L274-L291】【F:main.py†L3458-L3465】

**Last reviewed:** 2025-06-15

## Outstanding Findings

### Third-party Chart.js bundle loaded without integrity controls
- **Location:** `templates/admin_analytics.html`【F:templates/admin_analytics.html†L157-L160】
- **Impact:** The admin analytics dashboard pulls Chart.js directly from `cdn.jsdelivr.net` without a Subresource Integrity (SRI) hash or self-hosting. A compromised CDN response would execute arbitrary JavaScript in a privileged admin context, leading to full account takeover and data exfiltration.
- **Mitigation:** Pin and self-host the Chart.js bundle within `static/js/`, or reference the CDN asset with an SRI hash and strict versioning.

### Bootstrap Icons stylesheet served from CDN without integrity protection
- **Location:** `templates/layout.html`【F:templates/layout.html†L22-L30】
- **Impact:** The base layout links the Bootstrap Icons CSS from jsDelivr without integrity metadata. Malicious CSS delivered from the CDN can exfiltrate session data via `url()` beacons or visually spoof UI controls across every page.
- **Mitigation:** Ship the Bootstrap Icons assets from `static/` (or add an SRI hash) and tighten the CSP to only allow self-hosted stylesheets.

### Disposable email blocklist accepts non-HTTPS sources
- **Location:** `app/utils/disposable_email.py`【F:app/utils/disposable_email.py†L14-L52】
- **Impact:** When `DISPOSABLE_DOMAIN_URLS` includes plain-HTTP endpoints, the server downloads blocklists over an unauthenticated channel. A network attacker can alter the response to silently allow disposable domains (undermining anti-abuse) or block legitimate addresses, resulting in targeted denial of service during registration.
- **Mitigation:** Require HTTPS for remote blocklist URLs (reject or upgrade `http://` entries) and pin expected TLS certificates or ship curated lists with the release.
