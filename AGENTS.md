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
- Admin Manage Bars page uses `templates/admin_bars.html` with `.bars-page` styles in `static/css/components.css`. The page header stacks the title above the search and Add Bar controls
- Admin Manage Bars page includes a client-side name search via `#barsSearch`
- Admin Manage Bars actions use uppercase text-only pill buttons that expand to fit text; links and buttons inherit the base font so Delete matches Edit sizing while employing a brighter `.btn-danger-soft` red to deter accidental clicks
- Admin Manage Categories page uses `templates/bar_manage_categories.html` with `.menu-page` styles in `static/css/components.css`, a client-side category search via `#categorySearch`, and grouped uppercase action pills (`.btn-outline` for Products and Edit, `.btn-danger-soft` for Delete). The page header stacks the title above the search and Add Category controls
- Category edit and create forms live in `templates/bar_edit_category.html` and `templates/bar_new_category.html`; the description field uses a `<textarea>` styled by the `.form textarea` rule in `static/css/components.css`.
- Product edit and create forms live in `templates/bar_edit_product.html` and `templates/bar_new_product.html`; the description field uses a `<textarea>` styled by the `.form textarea` rule in `static/css/components.css`.
- Admin Manage Menu Items page uses `templates/bar_category_products.html`; wrapped in `.menu-page` with a `.menu-toolbar` header and Add Product button, listing products in a `.table-card`-wrapped `menu-table` with text-only pill buttons (`.btn-outline`, `.btn-danger-soft`) and a prominent Delete
- Admin Manage Users page uses `templates/admin_bar_users.html` with `.users-page` styles in `static/css/components.css`, a client-side username/email search via `#userSearch`, and grouped action pills. The page header stacks the title above an Add Existing User form and the search controls; new user creation has been removed
- Manage Bar Users list now shows only a red `Remove` button to unassign staff from the current bar; user editing is handled on the main Admin Users page
- Removing a user triggers a popup confirmation using `.cart-blocker` and `.cart-popup`
- Admin Manage Bars delete links open a popup confirmation using `.cart-blocker` and `.cart-popup`
- `BAR_CATEGORIES` defined in `main.py`; reused in `search.js` and `view-all.js`
- Categories stored in `bars.bar_categories`
- Edit Bar basic info page uses `.editbar` layout with `.grid-2` and `.card` sections (Map, Details, Media & Hours).
- Edit Bar cards remove the base mobile `max-height` so all content is visible on small screens.
- Categories are shown as always-visible chips synchronized with a hidden `<select id="categoriesNative" name="categories" multiple>`.
- Manual close checkbox (`#manual_closed`) toggles the `.hours-table` inputs.
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
  - `cart.html` displays the current bar's name, lists its tables for selection, and shows a wallet link for adding funds.
  - Checkout form asks for payment method (credit card, wallet credit, or pay at bar);
    selection is handled by `/cart/checkout` and stored in `Transaction.payment_method`.
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
  - `templates/bartender_orders.html` groups orders into `<ul>` lists with IDs
    `incoming-orders`, `preparing-orders`, `ready-orders`, and `completed-orders`.
  - The bartender dashboard lists assigned bars as `.bar-card` links to `/dashboard/bar/{id}/orders`.
  - The bar admin dashboard lists assigned bars as `.bar-card` items with edit and management links.
  - The bar admin dashboard uses `admin-dashboard` `editbar` styling with an `admin-identity` card mirroring the admin dashboard.
  - Each bar card includes buttons for editing the bar and managing orders via `/dashboard/bar/{id}/orders`.
  - Bar admins view live orders in `bar_admin_orders.html`, which mirrors the bartender view and adds an
    "Order History & Revenue" button linking to `/dashboard/bar/{id}/orders/history`.
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
- Order History & Revenue monthly cards use `card--placed` (blue) for the current month and `card--accepted` (orange) for past months; text color remains default.
- Past months show a "Confirm Payment" button to super admins; confirmed months switch to `card--ready` (green).
  - WebSocket endpoints `/ws/bar/{bar_id}/orders` and `/ws/user/{user_id}/orders` push real-time status updates.
  - WebSocket support depends on `uvicorn[standard]` (or another backend that provides the `websockets` library).
  - `static/js/orders.js` selects `ws` or `wss` based on the page protocol for secure deployments.
  - API endpoints `/api/bars/{bar_id}/orders` (GET) and `/api/orders/{id}/status` (POST) list and update orders for bartenders and bar admins.
  - `/api/bars/{bar_id}/orders` returns all statuses so completed orders remain visible after reloads.
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
    - Order views render each order as an `<article class="order-card card">` with header, meta, and items sections. Orders are grouped in `.order-list` containers for consistent styling.
    - Each order card exposes `data-status` with the raw status for client-side updates.
    - `.order-list` is a flex container that wraps so order cards can flow horizontally.
    - Order list cards are 395px wide on desktop and 315px on mobile, with 10px internal padding (was 5px) while allowing their height to expand with content.
    - Order cards override the base `card` max-height so they can grow to fit all text.
    - Order card backgrounds reflect status via `card--placed` (blue), `card--accepted` (orange), `card--ready` (green), `card--completed` (default surface), and `card--canceled` (red).
    - `.order-list .card__body` uses `gap: var(--space-1)` and removes default margins on child `p` and `ul` elements to tighten spacing.
    - Order card styles live in `static/css/components.css` under the `.order-card` block and dynamic rendering is handled by `static/js/orders.js`.
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
