# AGENT Notes

- Core modules:
  - `main.py` – routes and helpers
  - `models.py` – data models
  - `database.py` – database utilities
  - `audit.py` – records user actions to `AuditLog`
  - `finance.py` – VAT and payout calculations
  - `payouts.py` – schedule periodic payouts for bars
- Front-end mapping:
  - Styles in `static/css/components.css` (`components.min.css` for minified)
  - Templates live under `templates/`
  - JavaScript: `static/js/app.js` (shared/carousels), `static/js/search.js`, `static/js/view-all.js`
  - Bar & product card size: 400×450 desktop, 300×400 mobile
  - Global footer: `templates/layout.html` uses `.site-footer` styled in `static/css/components.css`
- Bars:
  - `/bars` page uses `templates/all_bars.html` and `static/js/view-all.js`
  - `BAR_CATEGORIES` defined in `main.py`; reused in `search.js` and `view-all.js`
  - Categories stored in `bars.bar_categories`
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
  - Bar edit options page links to table management (`templates/admin_bar_tables.html`) where staff can add, edit, and delete tables. Add and edit forms live in `templates/admin_bar_new_table.html` and `templates/admin_bar_edit_table.html`; table descriptions are for staff only
- Products:
  - Images stored in `menu_items.photo` and served via `/api/products/{id}/image`
  - `templates/bar_detail.html` shows products with carousels handled by `static/js/app.js`
- Cart:
  - `/bars/{bar_id}/add_to_cart` accepts POST form submissions
    and returns JSON `{count, totalFormatted, items[]}` when `Accept: application/json`
  - `/cart/update` and `/cart/checkout` also expect POST form data
  - `/cart/update` returns JSON when `Accept: application/json`
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
  - `cart.html` displays the current bar's name, lists its tables for selection, and shows a wallet link for adding funds.
  - Checkout form asks for payment method (credit card, wallet credit, or pay at bar);
    selection is handled by `/cart/checkout` and stored in `Transaction.payment_method`.
  - The popup offers "Remove products" (clears cart via `POST /cart/clear`) or "Go to the bar menu".
  - Wallet and top-up pages clear `cart_bar_id` to prevent the cart popup from appearing.
  - The top-up page at `/topup` renders `templates/topup.html` and suppresses the cart popup by passing `cart_bar_id` and `cart_bar_name` as `None`.
- Users:
  - Credit stored in `users.credit`; ensured by `ensure_credit_column()` on startup
  - Admin user edits clear old bar roles before saving new assignments
  - Admin user edits persist credit and current bar assignment; `_load_demo_user` hydrates both from the database
  - Admin users list loads each user's `bar_id` and `credit` directly from the database so assignments survive restarts
  - Admin user edits update passwords and refresh user caches so new assignments replace old data
  - Login fetches the user's bar assignment from the database so the bar is available immediately after authentication
  - Admin user edit form: `templates/admin_edit_user.html` posts fields
    (`username`, `password`, `email`, `prefix`, `phone`, `role`, `bar_ids`, `credit`)
    to `/admin/users/edit/{id}`. Bar selection uses checkboxes for easier multi-bar assignment.
  - Bar admins and bartenders may be assigned to multiple bars. `bar_ids` lists are used
    throughout to manage permissions and dashboard views.
- Orders:
  - `/orders` page renders `templates/order_history.html` with past `Order` entries for the current user.
  - Checkout persists orders to the database and redirects to `/orders`.
  - Mobile hamburger menu links to order history via `bi bi-clock-history` icon.
  - Bartenders manage live orders in `bartender_orders.html` using `static/js/orders.js`,
    which loads with `defer` and initializes `initBartender(bar.id)` on `DOMContentLoaded`.
  - The bartender dashboard lists assigned bars as `.bar-card` links to `/dashboard/bar/{id}/orders`.
  - WebSocket endpoints `/ws/bar/{bar_id}/orders` and `/ws/user/{user_id}/orders` push real-time status updates.
  - `static/js/orders.js` selects `ws` or `wss` based on the page protocol for secure deployments.
  - API endpoints `/api/bars/{bar_id}/orders` (GET) and `/api/orders/{id}/status` (POST) list and update orders.
  - Order status updates return the updated order; `static/js/orders.js` re-renders immediately after POST so bartenders see new states without reloading.
  - Bartender sees a single action button per order: Accept → Ready → Complete.
  - Order statuses progress `PLACED → ACCEPTED → READY → COMPLETED` (with optional `CANCELED/REJECTED`).
  - Valid transitions are enforced server-side via `ALLOWED_STATUS_TRANSITIONS` in `main.py`.
  - Order listings include customer name/phone, table, and line items for both bartender and user history.
  - Bartender dashboards prepend newly received orders to the list so the latest orders appear at the top.
  - `orders.js` sends a keep-alive ping every 30s so bartender WebSocket connections stay open and receive new orders instantly.
  - Bartender WebSocket connections automatically reconnect if the socket closes.
  - Orders store `payment_method`; `order.total` returns `subtotal + vat_total` and both fields are displayed in order listings.
  - `order_history.html` uses `order.customer_name`, `order.customer_prefix`, `order.customer_phone`, and `order.table_name` to avoid `None` errors when related records are missing.
  - `order_history.html` displays line items via `item.menu_item_name` to handle missing menu items gracefully.
  - Order cards display the bar's name via `order.bar_name`.
  - Order views render each order inside a `.card` and group them in `.order-list` containers for consistent styling.
  - Status labels are title-cased for display with `status status-<status>` classes (`formatStatus` in `orders.js`; `order.status|replace('_', ' ')|title` in templates).
  - `ensure_order_columns()` in `main.py` adds missing columns (e.g., `table_id`, `status`) to the `orders` table at startup.
- Testing:
  - Run `pytest`
