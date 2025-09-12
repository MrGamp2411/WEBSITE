# AGENT Notes

- Registration is a two-step flow. `/register` collects email and password and assigns a temporary `REGISTERING` role. Users are redirected to `/register/details` to supply username, phone prefix, and number, and cannot access other pages until this step completes.
- Registering users hitting any other route are redirected back to `/register/details` by middleware until step two finishes.
- Super admins can create users directly from the Admin Users page by entering only an email and password; this bypasses the normal registration flow and checks.
- Startup ensures the `roleenum` type contains `REGISTERING` via `ensure_role_enum()`.
- Display role users see only a two-column live orders screen (preparing/ready) at `/dashboard/bar/{id}/orders` with order codes only and no footer or cart links.
- Display role header removes navigation links and menu toggles; the logo is not clickable and only a Logout link remains.
- Display users are redirected from any non-display route to their bar's display orders page.
- The display orders page stretches to the full viewport width and doubles the size of order headers for clearer visibility.
- Display orders include 10px horizontal margins and center the order text within each card.

- Wallet page UI lives in `templates/wallet.html` using a `.wallet-page` wrapper and inline scoped styles. Transaction rows render inside `<ul id="txList">` as static `.tx` divs with no detail links. "Load more," "Export CSV," "Manage payment methods," and all filters have been removed; the "Top Up" button uses `text-decoration:none` to avoid an underline.
- Transaction detail views have been removed, so there is no `/wallet/tx/{index}` route or `transaction_detail.html` template.
- Wallet Recent Activity shows all transactions with the newest first, and wallet cards override the base mobile `max-height` so the feed length isn't capped.
- The balance card's meta now only shows an `Available` badge and omits any "last updated" text.
- Wallet transactions for orders begin in a `PROCESSING` state and update to `COMPLETED` once the order is accepted or to `CANCELED` if the order is canceled. Canceled transactions display a `- CHF 0.00` amount.
- Card payments finalized by the Wallee webhook are added to the wallet feed so card orders appear alongside wallet transactions. Pay-at-bar orders are excluded from the wallet feed.
- Top-ups append a `topup` transaction in a `PROCESSING` state during `/api/topup/init`; the Wallee webhook updates it to `COMPLETED` and refreshes the user's cached credit.
- Failed top-ups display a red `Failed` pill and a `+ CHF 0.00` amount in the wallet.
- Wallet transactions persist across restarts via the `wallet_transactions` table; login hydrates cached transactions from this table.
- User sessions survive server restarts by reloading missing user data from the database on demand.

- Core modules:
  - `main.py` – routes and helpers
  - `/cart/checkout` stores card order details in `Payment.raw_payload` and only creates the order when the Wallee webhook reports a successful payment; card payment failures leave the cart intact and skip order creation
    - The Wallee webhook clears the user's cart only after a `COMPLETED` payment so canceled or failed transactions leave items in the cart for retrying
  - `models.py` – data models
  - `database.py` – database utilities
  - `audit.py` – records user actions to `AuditLog`
  - `finance.py` – VAT and payout calculations
  - `payouts.py` – schedule periodic payouts for bars
  - `app/webhooks/wallee.py` – webhook endpoint for Wallee payments
    - Failed payment webhooks mark orders as `CANCELED` and set `cancelled_at`
- Wallet top-ups use Wallee: `/api/topup/init` creates `wallet_topups` records and credits the user when the webhook reports a completed transaction
    - Webhook `/webhooks/wallee` updates `wallet_topups` by `wallee_tx_id` with a row-level lock; processed records are skipped so repeated calls stay idempotent.
    - `wallet_topups` columns include `id`, `user_id`, `amount_decimal`, `currency`, `wallee_tx_id` (unique BIGINT), `status`, `processed_at`, `created_at`, and `updated_at`.
    - Save `int(tx.id)` to `wallet_topups.wallee_tx_id` and query by this field in the webhook.
    - Startup ensures these fields via `ensure_wallet_topup_columns()` which renames any legacy `wallee_transaction_id` column and sets the `status` default to `PENDING`.
    - The `payments` table tracks order payments only and no longer defines a `user_id` column.
    - Wallee API clients live in `app/wallee_client.py`; reuse the module's `tx_service`, `pp_service`, and `whenc_srv` instead of creating new clients.
    - Public keys returned by Wallee are base64‑encoded DER; signature checks should call `load_der_public_key` via `app/webhooks/wallee_verify.py`.
    - Amounts for `LineItemCreate` must be floats; passing `Decimal` values causes Wallee's SDK to raise an `AttributeError` during serialization.
    - Provide `amount_including_tax` for each `LineItemCreate`; the field is required by Wallee and replaces the deprecated `amount`.
  - `node-topup/` contains a TypeScript example service for initiating top-ups
  - Top-up flow:
    - `templates/topup.html` posts to `/api/topup/init`; non-2xx responses trigger a client alert "Unable to start top-up".
    - The submit button hides and disables after submission to prevent duplicate requests.
    - The endpoint requires authentication and accepts amounts between 1 and 1000 CHF.
    - Wallee integration uses `WALLEE_SPACE_ID`, `WALLEE_USER_ID`, and `WALLEE_API_SECRET`; misconfiguration results in an error.
    - If any of these variables are missing or invalid, `/api/topup/init` returns 503 "Top-up service unavailable".
    - `tests/test_topup_init.py` demonstrates record creation with patched Wallee services.
    - `/wallet/topup/failed` and `/wallet/topup/success` redirect to `/wallet` with `notice*` query parameters consumed by `static/js/app.js` to show cart-style popups.
  - Cart checkout:
    - `templates/cart.html` hides the "Place Order" button after form submission to prevent duplicate orders.
  - Front-end mapping:
    - Styles in `static/css/components.css` (`components.min.css` for minified)
    - Templates live under `templates/`
    - JavaScript: `static/js/app.js` (shared/carousels), `static/js/search.js`, `static/js/view-all.js`
    - Bar & product card size: 400×450 desktop, 300×400 mobile
  - Global footer: `templates/layout.html` uses `.site-footer` styled in `static/css/components.css`
- Bars:
  - `/bars` page uses `templates/all_bars.html` and `static/js/view-all.js`
  - Filters apply automatically on change; the old "Apply" button and its handler were removed
  - Public `/bars` listings show only bar names without numeric IDs, while admin listings keep each bar's `bar.id` zero-padded to three digits to match order codes
  - Admin Manage Bars page uses `templates/admin_bars.html` with `.bars-page` styles in `static/css/components.css`. The page header stacks the title above the search and Add Bar controls
- Admin Manage Bars page includes a client-side name search via `#barsSearch`
- Admin Manage Bars actions use uppercase text-only pill buttons that expand to fit text; links and buttons inherit the base font so Delete matches Edit sizing while employing a brighter `.btn-danger-soft` red to deter accidental clicks
- Admin Manage Payments page uses `templates/admin_payments.html`, reusing the `.users-page` layout classes (`.users-toolbar`, `.users-search`, `.users-table`) alongside `.payments-page` for admin tweaks. It includes a client-side bar search via `#paymentsSearch` and grouped action pills (`.btn-outline` for View/Add Test Closing, `.btn-danger-soft` for Delete Test Closing). The page header stacks the title above the search controls
- Admin Manage Categories page uses `templates/bar_manage_categories.html` with `.menu-page` styles in `static/css/components.css`, a client-side category search via `#categorySearch`, and grouped uppercase action pills (`.btn-outline` for Products and Edit, `.btn-danger-soft` for Delete). The page header stacks the title above the search and Add Category controls
- Category edit and create forms live in `templates/bar_edit_category.html` and `templates/bar_new_category.html`; the description field uses a `<textarea>` styled by the `.form textarea` rule in `static/css/components.css`.
- Product edit and create forms live in `templates/bar_edit_product.html` and `templates/bar_new_product.html`; the description field uses a `<textarea>` styled by the `.form textarea` rule in `static/css/components.css`.
- Admin Manage Menu Items page uses `templates/bar_category_products.html`; wrapped in `.menu-page` with a `.menu-toolbar` header and Add Product button, listing products in a `.table-card`-wrapped `menu-table` with text-only pill buttons (`.btn-outline`, `.btn-danger-soft`) and a prominent Delete
- Admin Manage Users page uses `templates/admin_bar_users.html` with `.users-page` styles in `static/css/components.css`, a client-side username/email search via `#userSearch`, and grouped action pills. The page header stacks the title above an Add Existing User form and the search controls; new user creation has been removed
- Manage Bar Users list now shows only a red `Remove` button to unassign staff from the current bar; user editing is handled on the main Admin Users page
- Removing a user triggers a popup confirmation using `.cart-blocker` and `.cart-popup`
- Cart popups stack action buttons vertically via `.cart-popup-actions`, and buttons expand full-width with consistent font size
- Admin Edit User page (`templates/admin_edit_user.html`) lists assigned bars separately from available bars, each with its own search (`#assignedBarSearch` and `#availableBarSearch`) and shows bar ID and city columns. Rows use Add/Remove pill buttons and hidden `bar_ids` checkboxes to track selections before save.
- Admin Edit User page includes a Delete button that opens a confirmation popup before removing the user.
- Super admins can assign the `Display` role from the Admin Edit User page, and any validation errors appear in a popup.
- Admin Manage Bars delete links open a popup confirmation using `.cart-blocker` and `.cart-popup`
- `BAR_CATEGORIES` defined in `main.py`; reused in `search.js` and `view-all.js`
- Categories stored in `bars.bar_categories`
- Edit Bar basic info page uses `.editbar` layout with `.grid-2` and `.card` sections (Map, Details, Media & Hours).
- Edit Bar cards remove the base mobile `max-height` so all content is visible on small screens.
- Categories are shown as always-visible chips synchronized with a hidden `<select id="categoriesNative" name="categories" multiple>`.
- Manual close checkbox (`#manual_closed`) toggles the `.hours-table` inputs.
- Manually closing a bar preserves its opening hours so they restore when reopened.
- Category chips allow selecting up to 5 items, disable others at the limit, and show a running count.
- Input fields on this page use a rounded "premium" style with a soft focus ring and invalid states.
- Name, Address, City, Canton, and Rating inputs share the pill-shaped `input-pill` style; `#description` textarea retains the focus ring.
- Save button sits at the bottom of the form in a `.save-inline` wrapper (non-sticky) and only appears once.
- Save button uses `.btn--primary` styling consistent with product and category forms.
- `Promo Label` and `Tags` fields have been removed from the project.
  - Opening hours data is sanitized; invalid or non-dict values are treated as closed
  - Category `sort_order` defaults to `0` when missing to avoid menu sorting errors
  - Bar detail page uses bar-card metadata for rating and geolocated distance
  - Bar detail page displays the bar's description beneath the address
  - Bar detail page shows open/closed status using `bar.is_open_now`
  - Bar detail page uses the same `.status` classes as bar cards for open/closed labels
  - Bar detail page lists weekly opening hours beneath the description
  - Bar detail info is rendered in `.bar-detail` (no card styling)
  - Bar detail layout: `.bar-cover` image (16/9), `.bar-meta` row with status/rating/distance, `.clamp`ed description, and `.bar-hours-card` grid (Mon–Thu / Fri–Sun)
  - `.bar-detail` has `margin-bottom: var(--space-4)` to add space before product categories
  - Open status uses `.status-open` (green) and closed status uses `.status-closed` (red)
  - Bar ordering pause state stored in `bars.ordering_paused` (BOOLEAN, defaults to FALSE)
  - Bar edit options page links to table management (`templates/admin_bar_tables.html`) where staff can add, edit, and delete tables. Add and edit forms live in `templates/admin_bar_new_table.html` and `templates/admin_bar_edit_table.html`; table descriptions use a `<textarea>` styled by the `.form textarea` rule and are for staff only
  - Admin Manage Tables page uses `templates/admin_bar_tables.html` with `.menu-page` styles, a client-side table search via `#tableSearch`, and grouped action pills (`.btn-outline` for Edit, `.btn-danger-soft` for Delete)
  - Deleting a table triggers a confirmation popup using `.cart-blocker` and `.cart-popup` like other admin pages
  - Edit Bar options UI uses `templates/admin_edit_bar_options.html` with `.bar-edit-page` and `.action-card` links in a 2-column grid (1 column on mobile)
- Products:
  - Images stored in `menu_items.photo` and served via `/api/products/{id}/image`
  - `templates/bar_detail.html` shows products with carousels handled by `static/js/app.js`
- Cart:
  - `/bars/{bar_id}/add_to_cart` accepts POST form submissions
    and returns JSON `{count, totalFormatted, items[]}` when `Accept: application/json`
  - `/cart/update` and `/cart/checkout` also expect POST form data
  - `/cart/update` returns JSON when `Accept: application/json`
  - Cart quantity "Update" button uses `.btn-outline` with black text for contrast
  - `static/js/app.js` uses a delegated submit listener on `.add-to-cart-form`
    to prevent page reloads. Rebuild `app.min.js` after changes.
  - After adding a product, the "Add to Cart" button becomes quantity controls
    handled in `static/js/app.js` and styled via `.qty-controls` in `static/css/components.css`
  - `/cart` returns JSON when `Accept: application/json` to hydrate quantity controls on load.
  - Quantity buttons `.qty-minus`/`.qty-plus` use the same `btn--primary btn--small` styling as "Add to Cart".
  - Quantity button clicks are delegated with `closest()` to support nested elements and desktop interactions.
  - Cart contents persist in the database via the `user_carts` table so they survive server restarts.
  - Cart items are limited to one bar at a time.
  - Navigating away from the active bar shows a blocking popup in `templates/layout.html` styled via `.cart-blocker` and `.cart-popup`.
  - The cart-blocker displays whenever the cart contains items from another bar, even if that bar's ordering is paused.
  - Bartenders can pause ordering from the orders dashboard; paused bars return 409 on `/bars/{id}/add_to_cart` and `app.js` shows a "service paused" popup.
  - The layout sets `window.orderingPaused` when the cart's bar is paused; `window.showServicePausedOnLoad` controls whether the popup opens automatically.
  - Menu pages pass `pause_popup_close` so the popup can be dismissed, while the cart page sets `pause_popup_back` and shows the popup on load with a "Back to the menu" button. The message advises contacting a staff member for more info.
  - `cart.html` lists available tables for selection and shows a wallet link for adding funds.
  - `cart.html` text is fully in English, including subtitle "Review your order, choose your table, and confirm payment." and payment method notes.
  - `cart.html` includes a disabled "Select table" placeholder so no table is chosen by default; checkout fails until a table is selected.
  - The `/cart` route clears `cart.table_id` when it doesn't match an available table so the placeholder remains the default.
  - The order total appears below the cart item list for quick review before selecting a table.
  - The checkout form places the "Message to bartender" textarea immediately after the table dropdown.
  - The cart product list is rendered inside a `.table-card` with a `.menu-table` for consistent styling with other lists.
  - Mobile view (≤768px) stacks cart, table form, notes, payment options, and summary in one column; the cart table scrolls horizontally inside a wrapper to preserve columns. The `.btn-primary.place-order` button sits at the end of the summary card above the global footer and does not stick to the viewport.
  - Checkout form asks for payment method (credit card, wallet credit, or pay at bar);
    selection is handled by `/cart/checkout` and stored in `Transaction.payment_method`.
  - The cart page uses a premium `.cart-page` wrapper with a wallet banner, summary sidebar, and scoped styles defined inline.
    Quantity update forms wrap inputs and buttons in `.qty-group` for compact stepper styling.
  - Credit card payments use Wallee; when credentials are present,
    `/cart/checkout` records a `payments` row with `wallee_tx_id` and
    redirects to Wallee's payment page. The `/webhooks/wallee` endpoint
    updates `payments.state` from webhook events.
  - Card orders are only broadcast after the webhook reports a successful
    state; failed payments automatically cancel the order.
  - Failed card payments redirect users back to `/cart` via Wallee's
    `failed_url` with `notice=payment_failed` so `static/js/app.js`
    shows a popup and the cart remains available for retrying.
  - Checkout form includes an optional "notes" textarea for special requests;
    notes are saved on orders and shown on bartender and user order cards.
  - The popup offers "Remove products" (clears cart via `POST /cart/clear`) or "Go to the bar menu".
  - Wallet and top-up pages clear `cart_bar_id` to prevent the cart popup from appearing.
  - The top-up page at `/topup` renders `templates/topup.html` and suppresses the cart popup by passing `cart_bar_id` and `cart_bar_name` as `None`.
- Users:
  - Credit stored in `users.credit`; ensured by `ensure_credit_column()` on startup
  - Admin user edits clear old bar roles before saving new assignments
  - Admin user edits persist credit and current bar assignment; `_load_demo_user` hydrates both from the database
- Admin users list loads each user's `bar_id` and `credit` directly from the database so assignments survive restarts
- Admin user edits update passwords and refresh user caches so new assignments replace old data
- Admin Manage Users page uses `templates/admin_users.html` with `.users-page` styles, a client-side username/email search via `#userSearch`, and grouped action pills (`View`, `Edit`) in each row
- Super admins can open `/admin/users/view/{id}` rendered by `templates/admin_view_user.html` to review a user's profile, orders, and audit logs
- The Orders table on this view displays each order's `public_order_code` or `#id` in the ID column to match order card formatting
- Login fetches the user's bar assignment from the database so the bar is available immediately after authentication
- Login and Register pages show text prompts linking to each other: "Already registered? Log in" and "Not registered yet? Register"
- Register form preserves entered username, email, phone number, and prefix when validation fails so users can correct errors without retyping.
- Register and profile forms offer phone prefixes for Switzerland (+41), Italy (+39), Germany (+49), and France (+33); USA and UK options have been removed.
- Register form requires a phone number with 9–10 digits; invalid entries show an error
- Register form rejects duplicate phone numbers; the combination of prefix and phone must be unique
- Register form requires an email in the format text@text.text; invalid entries show an error
- Register form enforces username rules: 3–24 characters, lowercase letters, numbers, dot, hyphen or underscore with no spaces or consecutive punctuation; reserved names (admin, root, api, login, support, www, siplygo) are rejected
- Register form requires passwords 8–128 characters long; common passwords like `12345678` are rejected. Passwords are hashed with Argon2id. Forms include show/hide toggles and a Caps Lock indicator.
- Register form includes a required `confirm_password` field that must match the password.
- Register and login forms use a flex `.password-wrapper` so the show/hide password toggle sits on the right side of the card.
- Profile page (`templates/profile.html`) lets logged-in users update username, email, password, prefix, and phone using the same validation rules as registration. `/profile` GET renders the form and `/profile` POST saves changes to the database and in-memory cache, logging the user out after password changes. Each field shows a Bootstrap pencil icon to indicate editability, and changing the password requires the current password for verification.
- Profile page UI wraps content in `.profile-page` and `.profile-card`, arranges fields in a responsive grid, groups phone prefix/number on desktop, includes a visual password strength meter, and keeps a sticky Save button inside the card.
- Profile page text inputs reuse the registration `.auth-card` styles (padding, border, default focus) for consistent text box appearance.
- Profile page edit pencils match the password toggle's minimal button style and sit on the right edge of each input.
- Profile fields start disabled and are unlocked by clicking their pencil icons; `static/js/profile.js` handles enabling inputs and re-disabling them after saving with a success message.
  - Admin user edit form: `templates/admin_edit_user.html` posts fields
    (`username`, `email`, `prefix`, `phone`, `role`, `bar_ids`, `add_credit`, `remove_credit`)
    to `/admin/users/edit/{id}`. Credit is adjusted by adding and subtracting these values. Password changes use
    `templates/admin_change_user_password.html` via
    `/admin/users/{id}/password` without requiring the current password.
    Bar selection uses checkboxes for easier multi-bar assignment.
  - Bar admins and bartenders may be assigned to multiple bars. `bar_ids` lists are used
    throughout to manage permissions and dashboard views.
- Orders:
  - `/orders` page renders `templates/order_history.html` with past `Order` entries for the current user.
  - Orders include a `public_order_code` formatted `BBB-DDMMAA-SEQ` using the bar's 3-digit ID, the Europe/Zurich order date, and a bar-local daily counter that resets at midnight.
  - The page wraps content in `.orders-page`; pending and completed sections show counts and empty states, and order cards sit in a responsive `.orders-grid` without altering card markup. The previous status/date/search/sort/export toolbar has been removed.
  - Desktop order grids expand to full width with wider cards (minimum 100px) while still capping at three columns.
  - Mobile order grids show a single column with a 100px minimum card width.
  - Order history lists all orders with no "Load more" button or "Back to top" link; the `.orders-actions` block was removed.
  - Checkout persists orders to the database and redirects to `/orders`.
  - Mobile hamburger menu links to order history via `bi bi-clock-history` icon.
- Mobile menu drops the "How it works" entry and adds a `bi bi-person` Profile link for logged-in users.
- Mobile menu close button sits on the left via `.menu-close{align-self:flex-start}`.
- Bartenders manage live orders in `bartender_orders.html` using `static/js/orders.js`,
    which loads with `defer` and initializes `initBartender(bar.id)` on `DOMContentLoaded`.
  - `templates/bartender_orders.html` wraps content in `.orders-page` and groups
    orders into `.orders-grid` containers with IDs `incoming-orders`,
    `preparing-orders`, `ready-orders`, and `completed-orders` for real-time lists.
  - The bartender dashboard lists assigned bars as `.bar-card` links to `/dashboard/bar/{id}/orders`.
  - The bartender dashboard uses `admin-dashboard` `editbar` styling with an `admin-header`, `admin-identity` card, and `admin-section` to match other dashboards.
  - The bar admin dashboard lists assigned bars as `.bar-card` items with edit and management links.
  - The bar admin dashboard uses `admin-dashboard` `editbar` styling with an `admin-identity` card mirroring the admin dashboard.
  - Each bar card includes buttons for editing the bar and managing orders via `/dashboard/bar/{id}/orders`.
  - Bar admins view live orders in `bar_admin_orders.html`, which mirrors the bartender view and adds an
    "Order History & Revenue" button linking to `/dashboard/bar/{id}/orders/history`.
  - Bartender and bar admin live order pages reuse the order history grid styles
    (`orders-page` wrapper with `orders-grid` for a single-column mobile layout and
    100px minimum card width).
  - Bars close automatically at their scheduled closing time based on `opening_hours`, moving completed
    orders into a `bar_closings` record (see `BarClosing` model). Canceled or rejected orders are also
    attached to the closing but do not count toward `total_revenue`. Editing a bar's hours immediately
    updates the automatic schedule.
- The Order History & Revenue page groups closings by month, showing total collected, total earned,
  and Siplygo commission (5% of total collected) for each month. Monthly "View" links point to
  `/dashboard/bar/{id}/orders/history/{year}/{month}` with the list of that month's closings, and
  individual daily summaries still link to `/dashboard/bar/{id}/orders/history/{closing_id}`.
- Daily closing views list a payment breakdown (credit card, wallet, etc.) for completed orders.
- Monthly and daily summary cards now also show payment breakdowns on their revenue cards.
- Monthly and daily revenue cards display "Amount to pay to bar" calculated as total collected minus pay-at-bar totals minus the Siplygo commission. Commission is calculated on the total collected.
- Revenue cards use `.revenue-card.rc` markup with `.rc-*` utility classes for layout and spacing. The header pairs the month label with a right-aligned "View" link, followed by four KPI rows and a payment breakdown list.
- Revenue cards remove the base mobile `max-height` so all KPI rows and payment details are visible on small screens.
- Order History & Revenue monthly cards use `card--placed` (blue) for the current month and `card--accepted` (orange) for past months; text color remains default.
- Past months show a "Confirm Payment" button to super admins; confirmed months switch to `card--ready` (green).
  - WebSocket endpoints `/ws/bar/{bar_id}/orders` and `/ws/user/{user_id}/orders` push real-time status updates.
  - WebSocket support depends on `uvicorn[standard]` (or another backend that provides the `websockets` library).
  - `static/js/orders.js` selects `ws` or `wss` based on the page protocol for secure deployments.
    - API endpoints `/api/bars/{bar_id}/orders` (GET) and `/api/orders/{id}/status` (POST) list and update orders for bartenders and bar admins.
    - `/api/bars/{bar_id}/orders` returns all statuses so completed orders remain visible after reloads.
    - Orders attached to a `BarClosing` (`closing_id` set) are excluded from `/api/bars/{bar_id}/orders` so dashboards show only current orders.
    - Order status updates return the updated order; `static/js/orders.js` re-renders immediately after POST so staff see new states without reloading.
    - Bartenders and bar admins can accept or cancel incoming orders; after acceptance, actions progress Ready → Complete.
  - Orders are grouped into four sections: Incoming (`PLACED`), Preparing (`ACCEPTED`), Ready (`READY`), and Completed (`COMPLETED`/`CANCELED`/`REJECTED`).
  - The `/orders` route treats `CANCELED` and `REJECTED` orders as completed so they're excluded from pending.
  - Order statuses progress `PLACED → ACCEPTED → READY → COMPLETED` (with optional `CANCELED/REJECTED`).
  - Valid transitions are enforced server-side via `ALLOWED_STATUS_TRANSITIONS` in `main.py`.
  - Order listings include customer name/phone, table, and line items for both bartender and user history.
  - Bartender dashboards list orders chronologically: completed orders show newest first, while incoming, preparing, and ready orders show oldest first.
  - Orders record `accepted_at` and `ready_at` timestamps; bartender cards show placement time and preparation duration via `orders.js`.
  - User order cards show placement time and preparation duration using `order_history.html` and `orders.js`.
  - `orders.js` sends a keep-alive ping every 30s so bartender WebSocket connections stay open and receive new orders instantly.
  - Bartender WebSocket connections automatically reconnect if the socket closes.
  - Orders store `payment_method`; `order.total` returns `subtotal + vat_total` and both fields are displayed in order listings.
  - `order_history.html` uses `order.customer_name`, `order.customer_prefix`, `order.customer_phone`, and `order.table_name` to avoid `None` errors when related records are missing.
  - `order_history.html` displays line items via `item.menu_item_name` to handle missing menu items gracefully.
  - Order cards display the bar's name via `order.bar_name`.
    - Order views render each order as an `<article class="order-card card">` with header, meta, and items sections. Orders are grouped in `#pending-orders` and `#completed-orders` containers that also carry an `orders-grid` class for responsive layout within `.orders-page`.
    - Each order card exposes `data-status` with the raw status for client-side updates. Inline script `initOrderHistoryCounts` updates badge counts and toggles empty states when orders change.
    - `.order-list` is a flex container that wraps so order cards can flow horizontally, but on the orders page this layout is overridden by `.orders-grid` to create a responsive grid without touching the cards.
    - Order list cards are 1000px wide on desktop and 315px on mobile, with 10px internal padding (was 5px) while allowing their height to expand with content.
    - Order cards override the base `card` max-height so they can grow to fit all text.
    - Order card backgrounds reflect status via `card--placed` (blue), `card--accepted` (orange), `card--ready` (green), `card--completed` (default surface), and `card--canceled` (red).
    - `.order-list .card__body` uses `gap: var(--space-1)` and removes default margins on child `p` and `ul` elements to tighten spacing.
    - Order card styles live in `static/css/components.css` under the `.order-card` block and dynamic rendering is handled by `static/js/orders.js`.
    - Order card headers stack the status chip under the order number using a column layout.
    - Meta sections use a two-column grid (`.order-kv`) ordered: Total, Placed, Customer, Bar, Table, Payment, Notes, Prep time. Customer phones render as neutral `tel:` links and item lists align quantity/name with ellipsis truncation.
  - `order_history.html` displays placement date and time via the `format_time` filter so displayed values honor `BAR_TIMEZONE`.
  - `orders.js` uses `formatTime` to show `YYYY-MM-DD HH:MM` strings on bartender and user order cards for clearer chronology.
  - Status labels are title-cased for display with `status status-<status>` classes (`formatStatus` in `orders.js`; `order.status|replace('_', ' ')|title` in templates).
  - `ensure_order_columns()` in `main.py` adds missing columns (e.g., `table_id`, `status`) to the `orders` table at startup.
- Cancelling an order refunds the total to the customer's wallet when paid by card or wallet; pay-at-bar orders are removed without refund.
- User cache (`users`) is updated when an order is canceled so the wallet shows the refunded credit.
- Order history and live order views display refund amounts for canceled orders.
- Customers may cancel their own `PLACED` orders from the order history page using the cancel button; this posts `CANCELED` via `/api/orders/{id}/status`.
- Admin dashboard includes a testing-only "Delete all orders" button at `/admin/orders/clear` to remove every order record.
- Admin dashboard groups actions into `.admin-section` grids using `.quick-card` links for Bars, Users, Payments, Analytics, Profile, and a Danger Zone.
- Super admin dashboard uses `editbar` styling and adds Bootstrap icons to card titles for Bars, Users, Payments, Analytics, Profile, and Danger Zone.
- Super admins can review bar revenue and orders via `/admin/payments`, listing all bars with "View" links to `/dashboard/bar/{id}/orders`.
- Super admins can view and update live orders for any bar using the same dashboards and APIs as bar admins and bartenders.
- `/admin/payments` offers testing helpers:
  - "Add Test Closing" creates a zero-revenue `BarClosing` dated to the first day of the previous month for the selected bar.
  - "Delete Test Closing" removes that test `BarClosing`.
- Testing:
  - Run `pytest`
- Meta:
  - Reverted merge commit 9bc986e (PR #315) in commit 11e13a9 to restore the bar admin dashboard to its previous state; `static/js/bar_admin_dashboard.js` was removed.
  - Reverted merge commit a169f9f (PR #359) and its fix commit 2617f16 to restore payout calculations to their previous logic.
- Profile page now collects username, email, and phone prefix/number only; a "Change Password" button links to `/profile/password` which uses `templates/change_password.html` and dedicated routes in `main.py`.
- Phone number fields on the profile page share the same rounded style as other inputs by styling `input[type="tel"]`.
- Change Password now sits under the phone number help text, and the Save button appears at the bottom-left without sticky behavior.
- Change Password button uses inline-flex styling to match the Save button size, and the password strength meter has been removed from the Change Password form.
- Change Password button is 25% smaller than the Save button using reduced font size and padding.
- Change Password fields stack in a single column on all screen sizes.
- Change Password Save button has added top margin to separate it from the Confirm Password field.
- Profile and Change Password pages display errors and warnings in red using `.alert-danger` or `.caps-warning`, and success messages in green via `.alert-success`.
- Disposable email enforcement:
  - Normalization and blocklist checks live in `app/utils/email_normalize.py` and `app/utils/disposable_email.py`.
  - CLI `python -m app.scripts.refresh_disposable_domains --force` refreshes the cache and writes `app/data/disposable_domains.snapshot`.
  - Dev endpoint `/internal/disposable-domains/stats` shows cache count and refresh time.
- Notifications:
  - `Notification` model in `models.py` stores per-user messages with optional image, attachment, and link.
  - Super admins send messages via `/admin/notifications`, targeting all users, a single user, or users who ordered at a specific bar.
  - The Admin Notifications page shows a table of recently sent messages above the form including recipient, subject, body, sent time, and sender.
  - Each send is logged to `NotificationLog` so broadcasts to all users appear once in the table instead of repeating per user.
  - Selecting a specific user or bar uses searchable tables; choosing "All Users" hides these selectors and does not require an ID.
  - The form disables hidden `user_id` and `bar_id` inputs when not targeting specific recipients and alerts if a required selection is missing.
  - Users view messages at `/notifications` with downloadable attachments and inline images.
    - Mobile menu includes `Notifications` link (`/notifications`) with `bi-bell` icon for accessing admin messages.
