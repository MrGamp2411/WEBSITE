# WEBSITE Agent Handbook (Repo Root)

This guide covers **every directory in `/workspace/WEBSITE`**. Use it as the
single reference for workflow rules, template locations, and asset mappings.
Sections are grouped so you can jump straight to the files you need.

## 1. Quick Reference

| Topic | Summary | Key Files |
| --- | --- | --- |
| Commit & PR titles | Max 30 characters. | `.git/` (enforced via instructions) |
| Phone validation copy | Must stay in English. | `app/phone.py`, `tests/test_register_phone_validation.py` |
| Dark mode | Removed; site is light-only. | Global |
| Recent work context | Always review latest commits. | `git log` |
| Session secret | Load via `SESSION_SECRET` env var; code falls back to random runtime secret only for local dev. | `main.py` |
| Leaflet assets | Self-hosted under `/static`; import via `url_for('static', ...)`. | `static/js/vendor/leaflet/`, `static/css/vendor/leaflet/` |

> **Reminder:** Inspect existing CSS/JS under `static/` before writing new
> assets. Templates under `templates/` must **not** contain inline CSS or JS.

## 2. Layout & Global Behaviour

- Core FastAPI app lives in `main.py`, with shared helpers in `database.py`,
  `models.py`, and `app/`.
- Shared template: `templates/layout.html` loads global scripts and hydrates
  JSON data via `static/js/layout.js` before `static/js/app.min.js` runs.
- `static/css/components.css` and `static/js/app.js` provide reusable UI
  patterns (mobile menu, language dialog, notification badges).
- Horizontal overflow is locked with `overflow-x: clip` on `html, body`; the
  header stretches to full width and sits at `z-index:1050`.
- Body uses a flex column with `min-height:100dvh`, ensuring `<main>` grows to
  keep the footer at the bottom.

## 3. Homepage (`templates/home.html`)

- Hero art asset: `photo/homepage.png`, served via `/photo`.
- Image markup: `<img class="hero-art" draggable="false">` with
  `user-select:none`.
- Positioning: `transform:translateX(-50%) rotate(70deg)`, offset
  `left:calc(50% - 450px)` plus an extra 150px down / 450px left.
- Size is fixed to 819×819 (20% smaller than original).
- Mobile offset adds another 100px downward (`bottom:calc(-8rem - 200px)`).
- `.home-hero .hero-art` styles live in `static/css/components.css`.
- Hero copy centers via `.home-hero .hero__content` with `margin-inline:auto`
  and `text-align:center`.
- Buttons: only "Browse Bars" remains, linking to `/search` and centered.

## 4. Authentication & Account Flow

| Route | Template | Assets | Notes |
| --- | --- | --- | --- |
| `/login` | `templates/login.html` | `static/js/login.js`, `static/css/pages/login.css` | Authenticated users redirect away. |
| `/register` (step 1) | `templates/register_step1.html` | `static/css/pages/register-step1.css` | Collects email + password, assigns `REGISTERING` role. |
| `/register/details` | `templates/register.html` | `static/js/register.js` | Forces lowercase usernames on input. |
| `/profile` | `templates/profile.html` | Translations under `profile` namespace. | Reuses phone prefixes. |
| `/change-password` | `templates/change_password.html` | Uses `auth` namespace for toggles. |

- Registration remains a two-step flow. After step two succeeds, users stay
  signed in and land on `/`.
- Middleware keeps `REGISTERING` users on `/register/details` and blocks other
  routes.
- Blocked/IP-blocked users cannot log out; middleware intercepts `/logout` and
  the layout hides that link.
- Super admins can create users from the Admin Users page with email +
  password only (bypasses registration flow).

## 5. Notifications System

- Templates: list at `templates/notifications.html`, detail at
  `templates/notification_detail.html`.
- Styling: `.notifications-list` and `.notification-card` in
  `static/css/components.css`. Unread items use `.card--unread` with light
  purple (`#EDE9FE`). Cards gain 25px horizontal margins in
  `.notifications-page .notification-card`.
- Behaviour: `/static/js/admin-notifications.js`,
  `/static/js/admin-notification-view.js`, `/static/js/admin-new-notification.js`.
  - Admin form enforces subject maxlength 30, handles attachments (downloadable
    in detail view) and optional targeting. Alerts when required recipient data
    is missing.
- Upload limits: images max 5MB (`ALLOWED_NOTIFICATION_IMAGE_TYPES`),
  attachments max 10MB (`ALLOWED_NOTIFICATION_ATTACHMENT_TYPES`). Filenames are
  sanitised via `sanitize_notification_filename` in `main.py`.
- Deleting a notification removes related `NotificationLog` plus all recipient
  `Notification` rows so `/notifications` stays in sync.
- Translations stored on both `NotificationLog` and each `Notification` via
  `subject_translations` and `body_translations` JSON columns.
- Users receive a welcome notification automatically after registration.
- Purge worker `purge_old_notifications_worker` deletes notifications older
  than 30 days.

## 6. Bar, Bartender, and Display Dashboards

| Area | Templates | CSS | JS | Notes |
| --- | --- | --- | --- | --- |
| Display orders | `templates/display_orders.html` | `static/css/pages/display-orders.css` | `static/js/display-page.js` | Two-column layout (preparing/ready), full-width, large headers. Display role redirects to this page only. |
| Bartender orders | `templates/bartender_orders.html` | `static/css/pages/bar-orders.css` | `static/js/bar-orders.js` | Shares layout with bar admin order dashboards. |
| Bar admin live orders | `templates/bar_admin_orders.html` | `static/css/pages/bar-orders.css` | `static/js/bar-orders.js` | Uses `initBartender` to manage pause toggles via `data-bar-id`. |
| Bar detail | `templates/bar_detail.html` | Shared components CSS | `static/js/bar-detail.js` | Syncs pause state, sets directions links, fallback imagery. |
| Bar search | `templates/search.html` | Shared components CSS | `static/js/search.js` | Handles filtering, metadata rendering, image fallbacks. |
| Home bar lists | `templates/home.html` | Shared CSS | `static/js/home.js` | Adds fallback handlers for hero and bar card images. |

- Display role header keeps only Logout, removes nav/menu links; logo is not
  clickable.
- Display orders page hides footer and cart links, doubling order header size
  for readability.
- Wallet top-up page (`templates/topup.html`) depends on `static/js/topup.js`
  for preset amounts and redirect handling.

## 7. Admin Area Overview

All admin edit pages now load CSS/JS externally. Use this table to locate
assets when working on admin templates under `templates/`.

| Template | CSS | JS | Extra Notes |
| --- | --- | --- | --- |
| `templates/admin_dashboard.html` | — | `static/js/admin-dashboard.js` | Handles delete-all-orders confirmation. |
| `templates/admin_analytics.html` | `static/css/pages/admin-analytics.css` | `static/js/admin-analytics.js` | Chart.js stays on CDN; data hydrates via `#adminAnalyticsData`. |
| `templates/admin_audit_logs.html` | `static/css/pages/admin-audit-logs.css` | `static/js/admin-audit-logs.js` | Keeps filter form responsive. |
| `templates/admin_notifications.html` | — | `static/js/admin-notifications.js` | Delete confirmation for notifications. |
| `templates/admin_notification_view.html` | `static/css/pages/admin-notification-view.css` | `static/js/admin-notification-view.js` | Styles actions, hides delete form. |
| `templates/admin_new_notification.html` | `static/css/pages/admin-new-notification.css` | `static/js/admin-new-notification.js` | Subject maxlength 30 enforced. |
| `templates/admin_edit_user.html` | `static/css/pages/admin-edit-user.css` | `static/js/admin-edit-user.js` | Delete spacing fixes, hides post form. |
| `templates/admin_edit_bar.html` | `static/css/pages/admin-edit-bar.css` | `static/js/admin-edit-bar.js` | Leaflet assets remain on CDN. |
| `templates/admin_edit_bar_options.html` | `static/css/pages/admin-edit-bar-options.css` | — | — |
| `templates/admin_edit_bar_description.html` | `static/css/pages/admin-edit-bar-description.css` | — | Handles multi-language bar descriptions. |
| `templates/admin_edit_welcome.html` | `static/css/pages/admin-edit-welcome.css` | `static/js/admin-edit-welcome.js` | — |
| `templates/admin_new_bar.html` | `static/css/pages/admin-new-bar.css` | `static/js/admin-new-bar.js` | Leaflet assets included separately; 120-character description inline. |
| `templates/admin_bars.html` | `static/css/pages/admin-bars.css` | `static/js/admin-bars.js` | JS manages table filtering + deletion; CSS hides delete forms. |
| `templates/admin_bar_users.html` | — | `static/js/admin-bar-users.js` | Handles staff filtering/removal dialogs. |
| `templates/admin_ip_block.html` | — | `static/js/admin-ip-block.js` | Delete confirmation. |
| `templates/admin_notifications_form` (search toolbars) | CSS via respective page | JS prevents submissions on `.form-search` wrappers. |
| `templates/admin_notification_view.html` | `static/css/pages/admin-notification-view.css` | `static/js/admin-notification-view.js` | Maintains action spacing. |

## 8. Bar Management (Admin + Bar Owner)

| Template | CSS | JS | Purpose |
| --- | --- | --- | --- |
| `templates/bar_manage_categories.html` | `static/css/pages/bar-manage-categories.css` | `static/js/bar-manage-categories.js` | Category listing + deletion handling. |
| `templates/bar_new_category.html` | `static/css/pages/bar-new-category.css` | `static/js/bar-new-category.js` | Category creation. |
| `templates/bar_edit_category.html` | `static/css/pages/bar-edit-category.css` | — | Category editing. |
| `templates/bar_edit_category_description.html` | `static/css/pages/translation-editor.css` | — | Translation editor shared with other description forms. |
| `templates/bar_edit_category_name.html` | `static/css/pages/translation-editor.css` | — | Name translation editor. |
| `templates/bar_category_products.html` | `static/css/pages/bar-category-products.css` | `static/js/bar-category-products.js` | Product deletion form handling. |
| `templates/bar_new_product.html` | Shared CSS | — | Uses `bar_products` translations namespace. |
| `templates/bar_edit_product.html` | `static/css/pages/bar-edit-product.css` | `static/js/bar-edit-product.js` (if added) | Loads via admin mapping above. |
| `templates/bar_edit_product_description.html` | `static/css/pages/translation-editor.css` | — | Product description translations. |

- Product image uploads (`/api/products/{product_id}/image`) now enforce staff-only access. Only super admins or bar admins/bartenders assigned to the product's bar can update imagery.

- Shared order widgets pull translations from `orders.statuses`,
  `orders.payment_methods`, `bartender_orders.actions`, and
  `display_orders.card.title` inside `app/i18n/translations/*.json`.
- Bar descriptions persist per language via `description_translations` JSON
  column. Creation seeds all languages; editing occurs at
  `/admin/bars/edit/{id}/description`.

## 9. Wallet & Finance

- Wallet top-up page translations live under the `wallet` namespace.
- Finance helpers located in `finance.py`, payouts handled in `payouts.py`, and
  top-up logic in `node-topup/`.

## 10. Static Marketing Pages

| Route | Template | Notes |
| --- | --- | --- |
| `/about` | `templates/about.html` | Intro: "Built and operated by Siply... We’re building a modern ordering experience..." |
| `/help` | `templates/help_center.html` | Pulls support contact from `main.py` constants. |
| `/for-bars` | `templates/for_bars.html` | Shares `.static-page` styles. |
| `/terms` | `templates/terms.html` | Uses `TERMS_VERSION` etc. from `main.py`. |

All static marketing pages reuse `.static-page` rules in
`static/css/components.css`. Support contact details live in Jinja globals inside
`main.py` (`SUPPORT_EMAIL`, `SUPPORT_NUMBER`, `TERMS_VERSION`, etc.).

## 11. Internationalisation

- Translation utilities: `app/i18n/__init__.py` with
  `translator_for_request(request)` for endpoints and `create_translator("<code>")`
  for background tasks.
- Resources stored in `app/i18n/translations/*.json`. Each language file includes
  metadata plus namespaces for page copy.
- `render_template` exposes helper context variables: `language_code`,
  `available_languages`, `_`, and `translate` (accept keyword formatting).
- Query parameter `?lang=<code>` updates session language; fallback order is
  session → `Accept-Language` → English.
- Namespaces per area (all in `app/i18n/translations/*.json`):
  - `about`, `help_center`, `for_bars`, `terms`, `wallet`
  - `login`, `register_step1`, `register`, `auth`
  - `profile`, `change_password`, `order_success`, `order_history`
  - `notifications`, `notification_detail`
  - `cart`, `search`, `bar_detail`, `all_bars`
  - `bartender_dashboard`, `bartender_orders`, `bartender_confirm`
  - `bar_admin_dashboard`, `bar_admin_orders`, `bar_admin_history`
  - `bar_categories`, `bar_products`
  - `orders.statuses`, `orders.payment_methods`, `bartender_orders.actions`,
    `display_orders.card.title`, `notices.payment_failed`,
    `notices.payment_success.close`
  - `admin_analytics`, `admin_audit_logs`, `admin_tables`, `admin_bar_users`,
    `admin_bars`, `admin_change_user_password`, `admin_dashboard`,
    `admin_edit_user`, `admin_users`, `admin_profile`, `admin_edit_bar_options`,
    `admin_notifications`, `admin_new_bar`, `admin_edit_welcome`,
    `admin_notification_view`, `admin_view_user`, `admin_edit_bar`,
    `admin_new_notification`, `admin_payments`, `topup`
- `tests/test_translations.py` ensures the four language files (English,
  Italiano, Français, Deutsch) exist, share key paths (excluding `_meta`), and
  contain non-empty strings.

## 12. Authentication, Redirects, and Middleware Notes

- `main.py` supplies `redirect_for_authenticated_user` to keep logged-in users
  off `/login` and `/register`.
- Registering users attempting other routes are redirected back to
  `/register/details`.
- Display users accessing non-display routes are redirected to their bar’s
  `/dashboard/bar/{id}/orders` page.
- Language menu now appears in the mobile navigation with a `bi-translate` icon
  and is managed via `static/js/app.js` plus `static/css/components.css`.
- Mobile menu `Notifications` entry uses `bi-bell`; unread counts show a red
  badge.

## 13. Orders & Payments

- Shared live order JS modules read translation namespaces listed above.
- Admin payments search logic moved to `static/js/admin-payments.js`; templates
  only render markup.
- Wallet top-up flow located in `templates/topup.html` with logic in
  `static/js/topup.js`.
- Node services for top-ups live under `node-topup/`.

## 14. Repository Documentation

- `README.md` functions as the complete product manual. Update it whenever
  features, routes, or assets change so engineering and operations stay aligned.

## 15. Security Pointers

- Public FastAPI endpoints under `/api/bars`, `/api/orders`, and `/api/payouts/run`
  currently lack authentication. Treat them as high-priority hardening targets
  during security-focused work.
- `/api/bars` POST now requires a super admin session; anonymous or non-admin
  attempts are logged to `AuditLog`.
- Product and bar photo uploads must route through `process_image_upload` in
  `main.py` so files are re-encoded to JPEG/PNG/WebP before storage.
- Browser hardening headers are enforced by
  `SecurityHeadersMiddleware` in `main.py`. Update the CSP allow-list before
  introducing new third-party JS, fonts, or map providers.
- Security review log (`SECURITY_REVIEW.md`) is kept empty unless a new finding
  is discovered. When adding an item include impact, mitigation, and remove it
  once the fix lands so the document always reflects the current backlog.
- Bootstrap Icons now live under `static/css/vendor/bootstrap-icons.css`; add the
  upstream `bootstrap-icons.woff2` and `.woff` binaries to `static/fonts/` when
  assembling deployment builds so navigation glyphs render correctly.
- Inter font weights 400/600/700 are self-hosted via
  `static/css/vendor/inter.css`. Keep matching `inter-latin-*-normal.woff2/.woff`
  binaries in `static/fonts/` (see the README there for download commands) so the
  base layout loads without reaching Google Fonts.

---

If any instruction seems missing, re-check this file—everything links to the
canonical location. For further context, inspect the file path referenced in
each table cell or bullet.

## Security Audit Notes

- Security findings are documented in `SECURITY_REVIEW.md`. The most recent
review (April 2025) highlights missing CSRF protections on POST routes and
unsafe product photo upload handling. Address these before deploying changes
that rely on cookie-authenticated flows or staff-provided media.
- May 2025 review uncovered: (1) stored XSS in the mini-cart because product
  names are injected with `innerHTML`, and (2) a CSRF gap where
  `/cart/select_table` mutates state via `GET`. See `SECURITY_REVIEW.md` for
  full details and remediation guidance.
- Search suggestions now build DOM nodes directly (see `renderSuggestions` in
  `static/js/app.js`) so bar metadata never passes through `innerHTML`. Cart
  notices also render with text nodes only, preventing HTML injection via query
  parameters.
- Live order dashboards (`static/js/orders.js`) still inject `order.notes`
  now populate order notes via text nodes (`.order-notes__value`) so customer
  input renders as plain text.
- May 2025 follow-up flagged new gaps (host header poisoning, spoofable
  `X-Forwarded-For`, and cart table selection without bar validation).
  These have been addressed: `HostValidationMiddleware` enforces an
  allow-listed origin derived from `BASE_URL`/`ALLOWED_HOSTS`,
  `get_request_ip` only trusts proxy headers from `TRUSTED_PROXY_IPS`, and
  table selections are now verified against the active cart bar before being
  persisted. Review `main.py` for implementation details.
- **May 2025 audit addendum:** New findings logged in `SECURITY_REVIEW.md`
  require attention:
  - `/login` casts optional latitude/longitude values with `float()` without
    validation, so malformed coordinates raise `ValueError` and return a 500.
  - `/api/orders/{order_id}/status` reveals whether an order exists because it
    returns 404 before authorization checks and 403 after them.
  - `/bar/{bar_id}/categories/{category_id}/products/{product_id}/edit`
    performs lookups and raises 404s prior to checking permissions, allowing
    unauthorized users to enumerate valid bar/category/product IDs.
- **June 2025 CSRF audit:** Login, registration, account management, cart, and
  admin POST forms still lack `enforce_csrf` checks. See the refreshed
  findings in `SECURITY_REVIEW.md` when hardening form submissions.
- **June 2025 vulnerability sweep:**
  - The `/bars` "All bars" filter chips still concatenate raw input into
    `chip.innerHTML`. Treat it as a DOM XSS sink until the component is rebuilt
    with `textContent` nodes (`static/js/view-all.js`).
  - `POST /api/bars` accepts arbitrary `photo_url` strings; anything not
    starting with `http(s)` is passed through by `make_absolute_url`, letting
    `data:image/svg+xml` payloads execute inside `<img>` tags. Force uploads
    through `save_product_image` when touching this API.
