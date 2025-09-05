"""
Simplified prototype of the SiplyGo platform using FastAPI and Jinja2 templates.

This application is not production‑ready but demonstrates the core building blocks
required to implement a premium bar ordering platform.  It includes:

* A home page that lists bars added through the admin interface.
* A bar detail page where customers can browse drink categories and add items to
  their cart.
* A session‑based cart implementation allowing quantity adjustments and order
  submission.
* Basic admin views to create and manage bars, categories, products and tables.

The code is organised to be easily extended with authentication, database
integration (e.g. PostgreSQL), role‑based permissions and real payment gateways.

To run the app locally:

```
uvicorn siplygo_app.main:app --reload
```

Then open http://localhost:8000 in your browser.

Limitations:
  - This prototype stores data in memory, so changes are lost on restart.
  - Authentication and role management are not implemented.  All users see the
    same admin panels for demonstration purposes.
  - Payment and order status updates are simulated.  Integration with real
    gateways (Stripe, Twint) and WebSocket notifications would require
    additional code.
"""

import os
import asyncio
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
    UploadFile,
    File,
    Response,
    Form,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import inspect, text, func, extract
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database import Base, SessionLocal, engine, get_db
from uuid import uuid4
from models import (
    Bar as BarModel,
    MenuItem,
    MenuVariant,
    Order,
    OrderItem,
    Payout,
    BarClosing,
    User,
    RoleEnum,
    UserBarRole,
    Category as CategoryModel,
    ProductImage,
    Table as TableModel,
    UserCart,
)
from pydantic import BaseModel, constr
from decimal import Decimal
from finance import (
    calculate_platform_fee,
    calculate_payout,
    calculate_vat_from_gross,
    PLATFORM_FEE_RATE,
)
from payouts import schedule_payout
from audit import log_action
from urllib.parse import urljoin

# Predefined categories for bars (used for filtering and admin forms)
BAR_CATEGORIES = [
    "Classic cocktail",
    "Mixology & Signature",
    "Wine bar (Merlot)",
    "Craft beer bar",
    "Pub / Irish pub",
    "Gastropub",
    "Sports bar",
    "Lounge bar",
    "Rooftop / Sky bar",
    "Speakeasy",
    "Live music / Jazz bar",
    "Piano bar",
    "Karaoke bar",
    "Club / Disco bar",
    "Aperitif & Snacks",
    "Coffee / Espresso bar",
    "Pastry bar",
    "Sandwich / Snack bar",
    "Gelato bar",
    "Local bar",
    "Lakefront / Lido",
    "Ticinese grotto",
    "Hotel bar",
    "Shisha / Hookah lounge",
    "Cigar & Whisky lounge",
    "Gin bar",
    "Rum / Tiki bar",
    "Tequila / Mezcaleria",
    "Billiards & Darts pub",
    "Afterwork / Business bar",
]

# -----------------------------------------------------------------------------
# Data models (in-memory for demonstration purposes)
# -----------------------------------------------------------------------------


class Category:
    def __init__(
        self,
        id: int,
        name: str,
        description: str,
        display_order: int = 0,
        photo_url: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.display_order = display_order
        self.photo_url = photo_url


class Product:
    def __init__(
        self,
        id: int,
        category_id: int,
        name: str,
        price: float,
        description: str,
        display_order: int = 0,
        photo_url: Optional[str] = None,
    ):
        self.id = id
        self.category_id = category_id
        self.name = name
        self.price = price
        # Ensure product descriptions stay within 190 characters
        self.description = description[:190]
        self.display_order = display_order
        self.photo_url = photo_url


class Table:
    def __init__(self, id: int, name: str, description: str = ""):
        self.id = id
        self.name = name
        self.description = description


class Bar:
    def __init__(
        self,
        id: int,
        name: str,
        address: str,
        city: str,
        state: str,
        latitude: float,
        longitude: float,
        description: str = "",
        photo_url: Optional[str] = None,
        rating: float = 0.0,
        is_open_now: bool = False,
        manual_closed: bool = False,
        ordering_paused: bool = False,
        opening_hours: Optional[Dict[str, Dict[str, str]]] = None,
        bar_categories: Optional[List[str]] = None,
    ):
        self.id = id
        self.name = name
        self.address = address
        self.city = city
        self.state = state
        self.latitude = latitude
        self.longitude = longitude
        self.description = description
        self.photo_url = photo_url
        self.rating = rating
        self.is_open_now = is_open_now
        self.manual_closed = manual_closed
        self.ordering_paused = ordering_paused
        self.opening_hours = opening_hours or {}
        self.bar_categories = bar_categories or []
        self.categories: Dict[int, Category] = {}
        self.products: Dict[int, Product] = {}
        self.tables: Dict[int, Table] = {}
        # Users assigned to this bar
        self.bar_admin_ids: List[int] = []
        self.bartender_ids: List[int] = []
        # Bartenders that still need to confirm the assignment
        self.pending_bartender_ids: List[int] = []


class DemoUser:
    def __init__(
        self,
        id: int,
        username: str,
        password: str,
        email: str = "",
        phone: str = "",
        prefix: str = "",
        role: str = "customer",
        bar_ids: Optional[List[int]] = None,
        pending_bar_id: Optional[int] = None,
        credit: float = 0.0,
    ):
        self.id = id
        self.username = username
        self.password = password
        self.email = email
        self.phone = phone
        self.prefix = prefix
        self.role = role
        self.bar_ids = bar_ids or []
        self.pending_bar_id = pending_bar_id
        self.credit = credit
        self.transactions: List[Transaction] = []

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"

    @property
    def is_bar_admin(self) -> bool:
        return self.role == "bar_admin"

    @property
    def is_bartender(self) -> bool:
        return self.role == "bartender"

    @property
    def bar_id(self) -> Optional[int]:
        return self.bar_ids[0] if self.bar_ids else None

    @bar_id.setter
    def bar_id(self, value: Optional[int]) -> None:
        self.bar_ids = [value] if value is not None else []


class CartItem:
    def __init__(self, product: Product, quantity: int = 1):
        self.product = product
        self.quantity = quantity

    @property
    def total(self) -> float:
        return self.product.price * self.quantity


class TransactionItem:
    def __init__(self, name: str, quantity: int, price: float):
        self.name = name
        self.quantity = quantity
        self.price = price

    @property
    def total(self) -> float:
        return self.price * self.quantity


class Transaction:
    def __init__(
        self,
        bar_id: int,
        bar_name: str,
        items: List[CartItem],
        total: float,
        payment_method: str,
    ):
        self.bar_id = bar_id
        self.bar_name = bar_name
        self.items = [
            TransactionItem(item.product.name, item.quantity, item.product.price)
            for item in items
        ]
        self.total = total
        self.payment_method = payment_method


class Cart:
    def __init__(self):
        self.items: Dict[int, CartItem] = {}
        self.table_id: Optional[int] = None
        self.bar_id: Optional[int] = None

    def add(self, product: Product):
        if product.id in self.items:
            self.items[product.id].quantity += 1
        else:
            self.items[product.id] = CartItem(product, 1)

    def remove(self, product_id: int):
        if product_id in self.items:
            del self.items[product_id]
        if not self.items:
            self.bar_id = None

    def update_quantity(self, product_id: int, quantity: int):
        if product_id in self.items:
            if quantity <= 0:
                del self.items[product_id]
            else:
                self.items[product_id].quantity = quantity
        if not self.items:
            self.bar_id = None

    def total_price(self) -> float:
        return sum(item.total for item in self.items.values())

    def clear(self):
        self.items.clear()
        self.table_id = None
        self.bar_id = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "items": [
                {"product_id": pid, "quantity": item.quantity}
                for pid, item in self.items.items()
            ],
            "table_id": self.table_id,
            "bar_id": self.bar_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Cart":
        cart = cls()
        cart.bar_id = data.get("bar_id")
        cart.table_id = data.get("table_id")
        bar = bars.get(cart.bar_id) if cart.bar_id else None
        if bar:
            for item in data.get("items", []):
                product = bar.products.get(item["product_id"])
                if product:
                    cart.items[product.id] = CartItem(product, item["quantity"])
        return cart


# -----------------------------------------------------------------------------
# Application initialisation
# -----------------------------------------------------------------------------

app = FastAPI()

# Mount a static files directory for CSS/JS/image assets if needed
app.mount("/static", StaticFiles(directory="static"), name="static")

# Allow cross-origin requests from configured frontends
origins_env = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable server-side sessions for authentication
app.add_middleware(SessionMiddleware, secret_key="dev-secret")


# -----------------------------------------------------------------------------
# WebSocket order update manager
# -----------------------------------------------------------------------------


class OrderWSManager:
    """Manages WebSocket connections for order updates."""

    def __init__(self):
        self.bar_connections: Dict[int, List[WebSocket]] = defaultdict(list)
        self.user_connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect_bar(self, bar_id: int, websocket: WebSocket):
        await websocket.accept()
        self.bar_connections[bar_id].append(websocket)

    async def connect_user(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.user_connections[user_id].append(websocket)

    def disconnect_bar(self, bar_id: int, websocket: WebSocket):
        if websocket in self.bar_connections.get(bar_id, []):
            self.bar_connections[bar_id].remove(websocket)

    def disconnect_user(self, user_id: int, websocket: WebSocket):
        if websocket in self.user_connections.get(user_id, []):
            self.user_connections[user_id].remove(websocket)

    async def broadcast_bar(self, bar_id: int, message: Dict[str, object]):
        for ws in list(self.bar_connections.get(bar_id, [])):
            try:
                await ws.send_json(message)
            except WebSocketDisconnect:
                self.disconnect_bar(bar_id, ws)

    async def broadcast_user(self, user_id: int, message: Dict[str, object]):
        for ws in list(self.user_connections.get(user_id, [])):
            try:
                await ws.send_json(message)
            except WebSocketDisconnect:
                self.disconnect_user(user_id, ws)


order_ws_manager = OrderWSManager()

# Allowed order state transitions
ALLOWED_STATUS_TRANSITIONS = {
    "PLACED": ["ACCEPTED", "REJECTED", "CANCELED"],
    "ACCEPTED": ["READY", "CANCELED"],
    "READY": ["COMPLETED", "CANCELED"],
    "COMPLETED": [],
    "CANCELED": [],
    "REJECTED": [],
}


async def send_order_update(order: Order) -> Dict[str, Any]:
    """Broadcast order updates to bartender and customer channels."""
    data = {
        "id": order.id,
        "status": order.status,
        "bar_id": order.bar_id,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name,
        "customer_prefix": order.customer_prefix,
        "customer_phone": order.customer_phone,
        "table_name": order.table_name,
        "bar_name": order.bar_name,
        "payment_method": order.payment_method,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "accepted_at": order.accepted_at.isoformat() if order.accepted_at else None,
        "ready_at": order.ready_at.isoformat() if order.ready_at else None,
        "total": order.total,
        "refund_amount": float(order.refund_amount or 0),
        "notes": order.notes,
        "items": [
            {
                "id": i.id,
                "menu_item_id": i.menu_item_id,
                "qty": i.qty,
                "menu_item_name": i.menu_item_name,
            }
            for i in order.items
        ],
    }
    await order_ws_manager.broadcast_bar(order.bar_id, {"type": "order", "order": data})
    if order.customer_id:
        await order_ws_manager.broadcast_user(order.customer_id, {"type": "order", "order": data})
    return data

def seed_super_admin():
    """Ensure a SuperAdmin user exists based on environment variables."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "ChangeMe!123")
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            password_hash = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()
            user = User(
                username=admin_email,
                email=admin_email,
                password_hash=password_hash,
                role=RoleEnum.SUPERADMIN,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


def ensure_prefix_column():
    """Add the `prefix` column to users table if it's missing."""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "prefix" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN prefix VARCHAR(10)"))


def ensure_credit_column() -> None:
    """Add the `credit` column to users table if it's missing."""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "credit" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN credit NUMERIC(10, 2) DEFAULT 0")
            )


def ensure_bar_columns() -> None:
    """Ensure recently added columns exist on the bars table."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("bars")}
    required = {
        "city": "VARCHAR(100)",
        "state": "VARCHAR(100)",
        "description": "TEXT",
        "rating": "FLOAT",
        "is_open_now": "BOOLEAN",
        "manual_closed": "BOOLEAN",
        "ordering_paused": "BOOLEAN DEFAULT FALSE",
        "opening_hours": "TEXT",
        "bar_categories": "TEXT",
    }
    missing = {name: ddl for name, ddl in required.items() if name not in columns}
    if missing:
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(
                    text(f"ALTER TABLE bars ADD COLUMN IF NOT EXISTS {name} {ddl}")
                )


def ensure_category_columns() -> None:
    """Ensure expected columns exist on the categories table."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("categories")}
    required = {"description": "TEXT", "photo_url": "VARCHAR(255)"}
    missing = {name: ddl for name, ddl in required.items() if name not in columns}
    if missing:
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(
                    text(
                        f"ALTER TABLE categories ADD COLUMN IF NOT EXISTS {name} {ddl}"
                    )
                )


def ensure_menu_item_columns() -> None:
    """Ensure expected columns exist on the menu_items table."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("menu_items")}
    required = {
        "sort_order": "INTEGER",
        "photo": "VARCHAR(255)",
    }
    missing = {name: ddl for name, ddl in required.items() if name not in columns}
    if missing:
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(
                    text(
                        f"ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS {name} {ddl}"
                    )
                )
    # Migrate legacy `photo_url` data to the new `photo` column if present.
    if ("photo" in columns or "photo" in missing) and "photo_url" in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE menu_items SET photo = photo_url "
                    "WHERE photo IS NULL AND photo_url IS NOT NULL"
                )
            )


def ensure_order_columns() -> None:
    """Ensure expected columns exist on the orders table."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("orders")}
    required = {
        "table_id": "INTEGER",
        "vat_total": "NUMERIC(10, 2) DEFAULT 0",
        "fee_platform_5pct": "NUMERIC(10, 2) DEFAULT 0",
        "payout_due_to_bar": "NUMERIC(10, 2) DEFAULT 0",
        "status": "VARCHAR(30) DEFAULT 'PLACED'",
        "payment_method": "VARCHAR(30)",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "accepted_at": "TIMESTAMP",
        "ready_at": "TIMESTAMP",
        "paid_at": "TIMESTAMP",
        "cancelled_at": "TIMESTAMP",
        "refund_amount": "NUMERIC(10, 2) DEFAULT 0",
        "notes": "TEXT",
        "source_channel": "VARCHAR(30)",
        "closing_id": "INTEGER",
    }
    missing = {name: ddl for name, ddl in required.items() if name not in columns}
    if missing:
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(text(f"ALTER TABLE orders ADD COLUMN {name} {ddl}"))


def ensure_bar_closing_columns() -> None:
    """Ensure expected columns exist on the bar_closings table."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("bar_closings")}
    if "payment_confirmed" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE bar_closings ADD COLUMN IF NOT EXISTS payment_confirmed BOOLEAN DEFAULT FALSE"
                )
            )


@app.on_event("startup")
async def on_startup():
    """Initialise database tables on startup."""
    Base.metadata.create_all(bind=engine)
    ensure_prefix_column()
    ensure_credit_column()
    ensure_bar_columns()
    ensure_category_columns()
    ensure_menu_item_columns()
    ensure_order_columns()
    ensure_bar_closing_columns()
    seed_super_admin()
    load_bars_from_db()
    asyncio.create_task(auto_close_bars_worker())


# Jinja2 environment for rendering HTML templates
templates_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# -----------------------------------------------------------------------------
# In-memory store with sample data
# -----------------------------------------------------------------------------

bars: Dict[int, Bar] = {}

# User storage
users: Dict[int, DemoUser] = {}
users_by_username: Dict[str, DemoUser] = {}
users_by_email: Dict[str, DemoUser] = {}
next_user_id = 1

# Cart storage per user
user_carts: Dict[int, Cart] = {}


def load_cart_from_db(user_id: int) -> Cart:
    with SessionLocal() as db:
        uc = db.get(UserCart, user_id)
        if uc and uc.items_json:
            data = {
                "items": json.loads(uc.items_json),
                "table_id": uc.table_id,
                "bar_id": uc.bar_id,
            }
            return Cart.from_dict(data)
    return Cart()


def save_cart_for_user(user_id: int, cart: Cart) -> None:
    with SessionLocal() as db:
        uc = db.get(UserCart, user_id)
        if not cart.items:
            if uc:
                db.delete(uc)
                db.commit()
            return
        if uc is None:
            uc = UserCart(user_id=user_id)
            db.add(uc)
        uc.bar_id = cart.bar_id
        uc.table_id = cart.table_id
        uc.items_json = json.dumps(cart.to_dict()["items"])
        db.commit()


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def get_current_user(request: Request) -> Optional[DemoUser]:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return users.get(user_id)


def get_cart_for_user(user: DemoUser) -> Cart:
    cart = user_carts.get(user.id)
    if cart is None:
        cart = load_cart_from_db(user.id)
        user_carts[user.id] = cart
    return cart


def slugify(value: str) -> str:
    """Convert a string to a simple slug."""
    return value.lower().replace(" ", "-")


def is_open_now_from_hours(hours: Dict[str, Dict[str, str]]) -> bool:
    """Determine if a bar should be open now based on its hours dict.

    The current time is evaluated in the timezone specified by the
    ``BAR_TIMEZONE`` environment variable (falling back to ``TZ`` if set).
    If neither variable is defined the server's local timezone is used.
    """
    if not isinstance(hours, dict):
        return False
    tz_name = os.getenv("BAR_TIMEZONE") or os.getenv("TZ")
    now = datetime.now(ZoneInfo(tz_name)) if tz_name else datetime.now()
    day = str(now.weekday())
    info = hours.get(day)
    if not info:
        return False
    open_time = info.get("open")
    close_time = info.get("close")
    if not open_time or not close_time:
        return False
    try:
        start = datetime.strptime(open_time, "%H:%M").time()
        end = datetime.strptime(close_time, "%H:%M").time()
    except ValueError:
        return False
    now_t = now.time()
    return start <= now_t < end


def auto_close_bars_once(db: Session, now: datetime) -> None:
    """Close completed orders for bars whose closing time has passed."""
    day = str(now.weekday())
    bars_to_check = db.query(BarModel).all()
    for bar in bars_to_check:
        if not bar.opening_hours:
            continue
        try:
            hours = json.loads(bar.opening_hours)
            info = hours.get(day)
            if not info:
                continue
            close_str = info.get("close")
            if not close_str:
                continue
            close_time = datetime.strptime(close_str, "%H:%M").time()
        except Exception:
            continue
        if now.time() < close_time:
            continue
        orders = (
            db.query(Order)
            .filter(
                Order.bar_id == bar.id,
                Order.status.in_(["COMPLETED", "CANCELED", "REJECTED"]),
                Order.closing_id.is_(None),
            )
            .all()
        )
        if not orders:
            continue
        total = sum(o.total for o in orders if o.status == "COMPLETED")
        closing = BarClosing(bar_id=bar.id, total_revenue=total, closed_at=now)
        db.add(closing)
        db.commit()
        for o in orders:
            o.closing_id = closing.id
        db.commit()


async def auto_close_bars_worker() -> None:
    """Periodic task to automatically close bars after their closing time."""
    while True:
        try:
            tz_name = os.getenv("BAR_TIMEZONE") or os.getenv("TZ")
            now = datetime.now(ZoneInfo(tz_name)) if tz_name else datetime.now()
            with SessionLocal() as db:
                auto_close_bars_once(db, now)
        except Exception:
            pass
        await asyncio.sleep(60)


def weekly_hours_list(
    hours: Optional[Dict[str, Dict[str, str]]],
) -> List[Dict[str, Optional[str]]]:
    """Return a list of weekly opening hours for display purposes.

    The input ``hours`` mapping uses string keys ``0``-``6`` for Monday-Sunday.
    Any missing or malformed entries are treated as closed for that day.
    """
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    if not isinstance(hours, dict):
        hours = {}
    result: List[Dict[str, Optional[str]]] = []
    for idx, day in enumerate(days):
        info = hours.get(str(idx)) if hours else None
        open_time = close_time = None
        if isinstance(info, dict):
            open_time = info.get("open")
            close_time = info.get("close")
        result.append({"day": day, "open": open_time, "close": close_time})
    return result


def format_time(dt: Optional[datetime]) -> str:
    """Format a UTC datetime to local YYYY-MM-DD HH:MM string using BAR_TIMEZONE/TZ."""
    if not dt:
        return ""
    tz_name = os.getenv("BAR_TIMEZONE") or os.getenv("TZ")
    tz = ZoneInfo(tz_name) if tz_name else None
    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    if tz:
        dt = dt.astimezone(tz)
    return dt.strftime("%Y-%m-%d %H:%M")

templates_env.filters["format_time"] = format_time


def is_bar_open_now(bar: BarModel) -> bool:
    """Determine if a bar is currently open considering manual closures."""
    if getattr(bar, "manual_closed", False):
        return False
    if not bar.opening_hours:
        return False
    try:
        hours = json.loads(bar.opening_hours)
    except Exception:
        return False
    if not isinstance(hours, dict):
        return False
    return is_open_now_from_hours(hours)


def load_bars_from_db() -> None:
    """Populate in-memory bars dict from the database."""
    db = SessionLocal()
    try:
        bars.clear()
        for b in db.query(BarModel).all():
            try:
                hours = json.loads(b.opening_hours) if b.opening_hours else {}
                if not isinstance(hours, dict):
                    hours = {}
            except Exception:
                hours = {}
            bar = Bar(
                id=b.id,
                name=b.name,
                address=b.address or "",
                city=b.city or "",
                state=b.state or "",
                latitude=float(b.latitude) if b.latitude is not None else 0.0,
                longitude=float(b.longitude) if b.longitude is not None else 0.0,
                description=b.description or "",
                photo_url=b.photo_url,
                rating=b.rating or 0.0,
                is_open_now=is_open_now_from_hours(hours)
                and not (b.manual_closed or False),
                manual_closed=b.manual_closed or False,
                ordering_paused=b.ordering_paused or False,
                opening_hours=hours,
                bar_categories=b.bar_categories.split(",") if b.bar_categories else [],
            )
            # Load categories for the bar
            for c in b.categories:
                bar.categories[c.id] = Category(
                    id=c.id,
                    name=c.name,
                    description=c.description or "",
                    display_order=c.sort_order if c.sort_order is not None else 0,
                    photo_url=c.photo_url,
                )
            # Load products for the bar
            for item in b.menu_items:
                bar.products[item.id] = Product(
                    id=item.id,
                    category_id=item.category_id,
                    name=item.name,
                    price=float(item.price_chf),
                    description=item.description or "",
                    display_order=item.sort_order or 0,
                    photo_url=f"/api/products/{item.id}/image",
                )
            # Load tables for the bar
            for t in b.tables:
                bar.tables[t.id] = Table(
                    id=t.id, name=t.name, description=t.description or ""
                )
            # Load user assignments
            bar.bar_admin_ids = []
            bar.bartender_ids = []
            bar.pending_bartender_ids = []
            roles = db.query(UserBarRole).filter(UserBarRole.bar_id == b.id).all()
            for r in roles:
                if r.role == RoleEnum.BARADMIN:
                    bar.bar_admin_ids.append(r.user_id)
                    if r.user_id in users:
                        if b.id not in users[r.user_id].bar_ids:
                            users[r.user_id].bar_ids.append(b.id)
                        users[r.user_id].role = "bar_admin"
                elif r.role == RoleEnum.BARTENDER:
                    bar.bartender_ids.append(r.user_id)
                    if r.user_id in users:
                        if b.id not in users[r.user_id].bar_ids:
                            users[r.user_id].bar_ids.append(b.id)
                        users[r.user_id].role = "bartender"
            bars[b.id] = bar
    finally:
        db.close()


def refresh_bar_from_db(bar_id: int, db: Session) -> Optional[Bar]:
    """Reload a single bar with its categories and products from the database."""
    b = db.get(BarModel, bar_id)
    if not b:
        return None
    bar = bars.get(bar_id)
    if not bar:
        try:
            hours = json.loads(b.opening_hours) if b.opening_hours else {}
            if not isinstance(hours, dict):
                hours = {}
        except Exception:
            hours = {}
        bar = Bar(
            id=b.id,
            name=b.name,
            address=b.address or "",
            city=b.city or "",
            state=b.state or "",
            latitude=float(b.latitude) if b.latitude is not None else 0.0,
            longitude=float(b.longitude) if b.longitude is not None else 0.0,
            description=b.description or "",
            photo_url=b.photo_url,
            rating=b.rating or 0.0,
            is_open_now=is_open_now_from_hours(hours)
            and not (b.manual_closed or False),
            manual_closed=b.manual_closed or False,
            ordering_paused=b.ordering_paused or False,
            opening_hours=hours,
        )
        bars[bar_id] = bar
    else:
        bar.name = b.name
        bar.address = b.address or ""
        bar.city = b.city or ""
        bar.state = b.state or ""
        bar.latitude = float(b.latitude) if b.latitude is not None else 0.0
        bar.longitude = float(b.longitude) if b.longitude is not None else 0.0
        bar.description = b.description or ""
        bar.photo_url = b.photo_url
        bar.rating = b.rating or 0.0
        try:
            hours = json.loads(b.opening_hours) if b.opening_hours else {}
            if not isinstance(hours, dict):
                hours = {}
        except Exception:
            hours = {}
        bar.opening_hours = hours
        bar.manual_closed = b.manual_closed or False
        bar.ordering_paused = b.ordering_paused or False
        bar.is_open_now = is_open_now_from_hours(hours) and not bar.manual_closed
        bar.categories.clear()
        bar.products.clear()
        bar.tables.clear()
    for c in b.categories:
        bar.categories[c.id] = Category(
            id=c.id,
            name=c.name,
            description=c.description or "",
            display_order=c.sort_order if c.sort_order is not None else 0,
            photo_url=c.photo_url,
        )
    for item in b.menu_items:
        bar.products[item.id] = Product(
            id=item.id,
            category_id=item.category_id,
            name=item.name,
            price=float(item.price_chf),
            description=item.description or "",
            display_order=item.sort_order or 0,
            photo_url=f"/api/products/{item.id}/image",
        )
    for t in b.tables:
        bar.tables[t.id] = Table(id=t.id, name=t.name, description=t.description or "")
    # Load user assignments
    bar.bar_admin_ids = []
    bar.bartender_ids = []
    bar.pending_bartender_ids = []
    roles = db.query(UserBarRole).filter(UserBarRole.bar_id == bar_id).all()
    for r in roles:
        if r.role == RoleEnum.BARADMIN:
            bar.bar_admin_ids.append(r.user_id)
            if r.user_id in users:
                if bar_id not in users[r.user_id].bar_ids:
                    users[r.user_id].bar_ids.append(bar_id)
                users[r.user_id].role = "bar_admin"
        elif r.role == RoleEnum.BARTENDER:
            bar.bartender_ids.append(r.user_id)
            if r.user_id in users:
                if bar_id not in users[r.user_id].bar_ids:
                    users[r.user_id].bar_ids.append(bar_id)
                users[r.user_id].role = "bartender"
    return bar


def make_absolute_url(url: Optional[str], request: Request) -> Optional[str]:
    if not url:
        return None
    if url.startswith("http://"):
        url = "https://" + url[len("http://") :]
    elif not url.startswith("https://"):
        url = urljoin(str(request.base_url), url.lstrip("/"))
    return url


async def save_upload(file, existing_path: Optional[str] = None) -> Optional[str]:
    """Persist an uploaded file and return its relative URL.

    If ``file`` has no filename, ``existing_path`` is returned unchanged."""
    filename = getattr(file, "filename", None)
    if filename:
        base_dir = Path(__file__).resolve().parent
        uploads_dir = base_dir / "static" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        _, ext = os.path.splitext(filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = uploads_dir / filename
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        await file.close()
        return f"/static/uploads/{filename}"
    return existing_path


def render_template(template_name: str, **context) -> HTMLResponse:
    request: Optional[Request] = context.get("request")
    if request is not None:
        user = get_current_user(request)
        context.setdefault("user", user)
        if user:
            cart = get_cart_for_user(user)
            context.setdefault(
                "cart_count",
                sum(item.quantity for item in cart.items.values()),
            )
            if cart.bar_id:
                bar = bars.get(cart.bar_id)
                if bar:
                    context.setdefault("cart_bar_id", bar.id)
                    context.setdefault("cart_bar_name", bar.name)
                    context.setdefault("cart_bar_paused", bar.ordering_paused)
        bar_obj = context.get("bar")
        if bar_obj and hasattr(bar_obj, "id"):
            context.setdefault("current_bar_id", bar_obj.id)
        recent_ids = request.session.get("recent_bar_ids", [])
        if recent_ids:
            with SessionLocal() as db:
                recent_bars = []
                for bar_id in reversed(recent_ids):
                    bar = db.get(BarModel, bar_id)
                    if bar:
                        bar.photo_url = make_absolute_url(bar.photo_url, request)
                        bar.is_open_now = is_bar_open_now(bar)
                        _ = bar.categories  # preload categories for search filters
                        recent_bars.append(bar)
                context.setdefault("recent_bars", recent_bars)

    # Ensure Google Maps API key is available to templates from environment.
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if api_key:
        context.setdefault("GOOGLE_MAPS_API_KEY", api_key)

    template = templates_env.get_template(template_name)
    return HTMLResponse(template.render(**context))


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


@app.post("/api/products/{product_id}/image")
async def upload_product_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not image.filename:
        raise HTTPException(status_code=400, detail="Nessun file")
    data = await image.read()
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File non immagine")
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File troppo grande (>5MB)")
    db_item = db.get(MenuItem, product_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Product not found")
    img = db.query(ProductImage).filter_by(product_id=product_id).first()
    if img:
        img.data = data
        img.mime = image.content_type
    else:
        db.add(ProductImage(product_id=product_id, data=data, mime=image.content_type))
    db.commit()
    refresh_bar_from_db(db_item.bar_id, db)
    return Response(status_code=204)


@app.get("/api/products/{product_id}/image")
def get_product_image(product_id: int, db: Session = Depends(get_db)):
    img = db.query(ProductImage).filter_by(product_id=product_id).first()
    if not img:
        raise HTTPException(status_code=404)
    headers = {"Cache-Control": "public, max-age=31536000, immutable"}
    return Response(content=img.data, media_type=img.mime, headers=headers)


# Basic demo routes. Real applications would include additional error handling
# and persistent storage.


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page listing available bars."""
    db_bars = db.query(BarModel).all()
    for bar in db_bars:
        bar.photo_url = make_absolute_url(bar.photo_url, request)
        bar.is_open_now = is_bar_open_now(bar)
    return render_template("home.html", request=request, bars=db_bars)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two lat/lon points."""
    from math import asin, cos, radians, sin, sqrt

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return 6371 * c


@app.get("/search", response_class=HTMLResponse)
async def search_bars(
    request: Request,
    q: str = "",
    lat: float | None = None,
    lng: float | None = None,
    db: Session = Depends(get_db),
):
    term = q.lower()
    db_bars = db.query(BarModel).all()
    for bar in db_bars:
        bar.photo_url = make_absolute_url(bar.photo_url, request)
        bar.is_open_now = is_bar_open_now(bar)
        if (
            lat is not None
            and lng is not None
            and bar.latitude is not None
            and bar.longitude is not None
        ):
            bar.distance_km = _haversine_km(
                float(lat), float(lng), float(bar.latitude), float(bar.longitude)
            )
        else:
            bar.distance_km = None
    results = [
        bar
        for bar in db_bars
        if term in (bar.name or "").lower()
        or term in (bar.address or "").lower()
        or term in (bar.city or "").lower()
        or term in (bar.state or "").lower()
    ]
    # Determine a random selection of open bars within 20km for the "Recommended" section.
    if lat is not None and lng is not None:
        nearby_pool = [
            b
            for b in db_bars
            if b.is_open_now and b.distance_km is not None and b.distance_km <= 20
        ]
    else:
        nearby_pool = [b for b in db_bars if b.is_open_now]
    recommended_bars = random.sample(nearby_pool, min(5, len(nearby_pool)))
    if lat is not None and lng is not None:
        rated_within = [
            b
            for b in results
            if b.rating is not None and b.distance_km is not None and b.distance_km <= 5
        ]
        rated_within.sort(key=lambda b: (-b.rating, b.distance_km))
        top_bars = rated_within[:5]
        top_bars_message = None
        if not top_bars:
            top_bars_message = "No bars near you."
        # Sort search results by proximity when location is provided
        results.sort(key=lambda b: (b.distance_km is None, b.distance_km))
    else:
        rated = [b for b in results if b.rating is not None]
        rated.sort(key=lambda b: -b.rating)
        top_bars = rated[:5]
        if len(top_bars) < 5:
            others = [b for b in results if b not in top_bars]
            others.sort(key=lambda b: (b.name or ""))
            top_bars.extend(others[: 5 - len(top_bars)])
        top_bars_message = None
        # Default to alphabetical order when distance is unavailable
        results.sort(key=lambda b: (b.name or "").lower())

    return render_template(
        "search.html",
        request=request,
        bars=results,
        top_bars=top_bars,
        top_bars_message=top_bars_message,
        recommended_bars=recommended_bars,
        query=q,
    )


@app.get("/bars", response_class=HTMLResponse)
async def list_all_bars(
    request: Request,
    lat: float | None = None,
    lng: float | None = None,
    db: Session = Depends(get_db),
):
    db_bars = db.query(BarModel).all()
    for bar in db_bars:
        bar.photo_url = make_absolute_url(bar.photo_url, request)
        bar.is_open_now = is_bar_open_now(bar)
        if (
            lat is not None
            and lng is not None
            and bar.latitude is not None
            and bar.longitude is not None
        ):
            bar.distance_km = _haversine_km(
                float(lat), float(lng), float(bar.latitude), float(bar.longitude)
            )
        else:
            bar.distance_km = None
    db_bars.sort(key=lambda b: (b.distance_km is None, b.distance_km))
    return render_template("all_bars.html", request=request, bars=db_bars)


@app.get("/api/search")
async def api_search(q: str = "", request: Request = None):
    term = q.lower()
    results = [
        {
            "id": bar.id,
            "name": bar.name,
            "address": bar.address,
            "city": bar.city,
            "state": bar.state,
            "description": bar.description,
            "photo_url": (
                make_absolute_url(bar.photo_url, request) if request else bar.photo_url
            ),
        }
        for bar in bars.values()
        if term in bar.name.lower()
        or term in bar.address.lower()
        or term in bar.city.lower()
        or term in bar.state.lower()
    ]
    return {"bars": results}


# -----------------------------------------------------------------------------
# Simple database-backed Bar API
# -----------------------------------------------------------------------------


class BarCreate(BaseModel):
    name: str
    slug: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    description: Optional[constr(max_length=120)] = None
    photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = 0.0
    is_open_now: Optional[bool] = False
    opening_hours: Optional[Dict[str, Dict[str, str]]] = None
    manual_closed: Optional[bool] = False
    ordering_paused: Optional[bool] = False
    bar_categories: Optional[str] = None


class BarRead(BaseModel):
    id: int
    name: str
    slug: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: float = 0.0
    is_open_now: bool = False
    opening_hours: Optional[Dict[str, Dict[str, str]]] = None
    manual_closed: bool = False
    ordering_paused: bool = False
    bar_categories: Optional[str] = None

    class Config:
        orm_mode = True


class OrderItemInput(BaseModel):
    menu_item_id: int
    qty: int = 1


class OrderCreate(BaseModel):
    bar_id: int
    items: List[OrderItemInput]


class OrderRead(BaseModel):
    id: int
    subtotal: float
    vat_total: float
    fee_platform_5pct: float
    payout_due_to_bar: float
    status: str
    payment_method: Optional[str] = None
    created_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    total: float
    refund_amount: float = 0
    notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_prefix: Optional[str] = None
    customer_phone: Optional[str] = None
    table_name: Optional[str] = None
    bar_name: Optional[str] = None

    class Config:
        orm_mode = True


class OrderItemRead(BaseModel):
    id: int
    menu_item_id: int
    qty: int
    menu_item_name: Optional[str] = None

    class Config:
        orm_mode = True


class OrderWithItemsRead(OrderRead):
    items: List[OrderItemRead]


class OrderStatusUpdate(BaseModel):
    status: str


class PayoutRunInput(BaseModel):
    bar_id: int
    period_start: datetime
    period_end: datetime
    actor_user_id: Optional[int] = None


class PayoutRead(BaseModel):
    id: int
    bar_id: int
    amount_chf: float
    period_start: datetime
    period_end: datetime
    status: str

    class Config:
        orm_mode = True


@app.get("/api/bars", response_model=List[BarRead])
def list_bars(db: Session = Depends(get_db)):
    """Return all bars stored in the database."""
    bars = db.query(BarModel).all()
    for b in bars:
        b.is_open_now = is_bar_open_now(b)
    return bars


@app.post("/api/bars", response_model=BarRead, status_code=status.HTTP_201_CREATED)
def create_bar(data: BarCreate, db: Session = Depends(get_db)):
    """Create a new bar in the database."""
    bar = BarModel(**data.dict())
    db.add(bar)
    db.commit()
    db.refresh(bar)
    return bar


@app.post("/api/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create an order and compute platform fee and payout."""
    bar = db.get(BarModel, order.bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")

    subtotal = Decimal("0.00")
    vat_total = Decimal("0.00")
    order_items: List[OrderItem] = []

    for item in order.items:
        menu_item = db.get(MenuItem, item.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        price = Decimal(menu_item.price_chf)
        line_total = price * item.qty
        line_vat = (
            calculate_vat_from_gross(price, Decimal(menu_item.vat_rate)) * item.qty
        )
        vat_total += line_vat
        subtotal += line_total - line_vat
        order_items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                qty=item.qty,
                unit_price=price,
                line_vat=line_vat,
                line_total=line_total,
            )
        )

    fee = calculate_platform_fee(subtotal)
    total_gross = subtotal + vat_total
    payout = calculate_payout(total_gross, fee)

    db_order = Order(
        bar_id=order.bar_id,
        subtotal=subtotal,
        vat_total=vat_total,
        fee_platform_5pct=fee,
        payout_due_to_bar=payout,
        status="PLACED",
        items=order_items,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    await send_order_update(db_order)
    return db_order


@app.post(
    "/api/payouts/run", response_model=PayoutRead, status_code=status.HTTP_201_CREATED
)
def run_payout(data: PayoutRunInput, db: Session = Depends(get_db)):
    """Aggregate completed orders for a bar within a date range and create a payout."""
    try:
        payout = schedule_payout(db, data.bar_id, data.period_start, data.period_end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    log_action(
        db,
        actor_user_id=data.actor_user_id,
        action="payout_run",
        entity_type="payout",
        entity_id=payout.id,
        payload={
            "bar_id": data.bar_id,
            "period_start": data.period_start.isoformat(),
            "period_end": data.period_end.isoformat(),
        },
    )
    return payout


@app.get("/bars/{bar_id}", response_class=HTMLResponse)
async def bar_detail(request: Request, bar_id: int):
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    bar.photo_url = make_absolute_url(bar.photo_url, request)
    bar.distance_km = None
    recent = request.session.get("recent_bar_ids", [])
    if bar.id in recent:
        recent.remove(bar.id)
    recent.append(bar.id)
    if len(recent) > 5:
        recent = recent[-5:]
    request.session["recent_bar_ids"] = recent
    # group products by category
    products_by_category: Dict[Category, List[Product]] = {}
    for prod in bar.products.values():
        prod.photo_url = make_absolute_url(prod.photo_url, request)
        category = bar.categories.get(prod.category_id)
        if not category:
            continue
        products_by_category.setdefault(category, []).append(prod)
    for prods in products_by_category.values():
        prods.sort(key=lambda p: p.display_order)
    sorted_products = sorted(
        products_by_category.items(), key=lambda kv: kv[0].display_order
    )
    return render_template(
        "bar_detail.html",
        request=request,
        bar=bar,
        products_by_category=sorted_products,
        opening_hours=weekly_hours_list(bar.opening_hours) if bar.opening_hours else [],
        pause_popup_close=bar.ordering_paused,
        cart_bar_name=bar.name,
        cart_bar_id=bar.id,
    )


@app.post("/bars/{bar_id}/add_to_cart")
async def add_to_cart(request: Request, bar_id: int, product_id: int = Form(...)):
    """Add a product to the cart from a submitted form."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if getattr(bar, "ordering_paused", False):
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse({"error": "ordering_paused"}, status_code=409)
        raise HTTPException(status_code=403, detail="Ordering is paused")
    product = bar.products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    cart = get_cart_for_user(user)
    if cart.bar_id and cart.bar_id != bar_id:
        products_by_category: Dict[Category, List[Product]] = {}
        for prod in bar.products.values():
            category = bar.categories.get(prod.category_id)
            if not category:
                continue
            products_by_category.setdefault(category, []).append(prod)
        return render_template(
            "bar_detail.html",
            request=request,
            bar=bar,
            products_by_category=products_by_category,
            error="Please clear your cart before ordering from another bar.",
            pause_popup_close=bar.ordering_paused,
            cart_bar_name=bar.name,
            cart_bar_id=bar.id,
        )
    if cart.bar_id is None:
        cart.bar_id = bar_id
    cart.add(product)
    save_cart_for_user(user.id, cart)
    if "application/json" in request.headers.get("accept", ""):
        count = sum(item.quantity for item in cart.items.values())
        total = cart.total_price()
        items = [
            {
                "id": item.product.id,
                "name": item.product.name,
                "qty": item.quantity,
                "price": f"CHF {item.product.price:.2f}",
                "lineTotal": f"CHF {item.total:.2f}",
            }
            for item in cart.items.values()
        ]
        return JSONResponse(
            {"count": count, "totalFormatted": f"CHF {total:.2f}", "items": items}
        )
    return RedirectResponse(
        url=f"/bars/{bar_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cart = get_cart_for_user(user)
    current_bar: Optional[Bar] = bars.get(cart.bar_id) if cart.bar_id else None
    if "application/json" in request.headers.get("accept", ""):
        count = sum(item.quantity for item in cart.items.values())
        total = cart.total_price()
        items = [
            {
                "id": item.product.id,
                "name": item.product.name,
                "qty": item.quantity,
                "price": f"CHF {item.product.price:.2f}",
                "lineTotal": f"CHF {item.total:.2f}",
            }
            for item in cart.items.values()
        ]
        return JSONResponse(
            {"count": count, "totalFormatted": f"CHF {total:.2f}", "items": items}
        )
    return render_template(
        "cart.html",
        request=request,
        cart=cart,
        bar=current_bar,
        pause_popup_back=current_bar.ordering_paused if current_bar else False,
        show_service_paused=current_bar.ordering_paused if current_bar else False,
    )


@app.post("/cart/clear")
async def clear_cart(request: Request):
    """Remove all items from the user's cart."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cart = get_cart_for_user(user)
    cart.clear()
    save_cart_for_user(user.id, cart)
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"cleared": True})
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/cart/update")
async def update_cart(
    request: Request, product_id: int = Form(...), quantity: int = Form(...)
):
    """Update item quantity or remove an item in the cart."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cart = get_cart_for_user(user)
    cart.update_quantity(product_id, quantity)
    save_cart_for_user(user.id, cart)
    if "application/json" in request.headers.get("accept", ""):
        count = sum(item.quantity for item in cart.items.values())
        total = cart.total_price()
        items = [
            {
                "id": item.product.id,
                "name": item.product.name,
                "qty": item.quantity,
                "price": f"CHF {item.product.price:.2f}",
                "lineTotal": f"CHF {item.total:.2f}",
            }
            for item in cart.items.values()
        ]
        return JSONResponse(
            {"count": count, "totalFormatted": f"CHF {total:.2f}", "items": items}
        )
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/cart/select_table")
async def select_table(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    try:
        table_id = int(request.query_params.get("table_id", 0))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid table")
    cart = get_cart_for_user(user)
    cart.table_id = table_id
    save_cart_for_user(user.id, cart)
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/cart/checkout")
async def checkout(
    request: Request,
    table_id: Optional[int] = Form(None),
    payment_method: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cart = get_cart_for_user(user)
    if table_id is not None:
        cart.table_id = table_id
    if cart.table_id is None:
        raise HTTPException(
            status_code=400, detail="Please select a table before checking out"
        )
    order_total = cart.total_price()
    if payment_method == "wallet":
        if user.credit < order_total:
            raise HTTPException(status_code=400, detail="Insufficient credit")
        user.credit -= order_total
        db_user = db.query(User).filter(User.id == user.id).first()
        if db_user:
            db_user.credit = user.credit
            db.commit()
    bar = bars.get(cart.bar_id) if cart.bar_id else None
    order_items = [
        OrderItem(
            menu_item_id=item.product.id,
            qty=item.quantity,
            unit_price=item.product.price,
            line_total=item.product.price * item.quantity,
        )
        for item in cart.items.values()
    ]
    db_order = Order(
        bar_id=cart.bar_id,
        customer_id=user.id,
        table_id=cart.table_id,
        subtotal=order_total,
        status="PLACED",
        payment_method=payment_method,
        paid_at=datetime.utcnow(),
        items=order_items,
        notes=notes,
    )
    db.add(db_order)
    db.commit()
    await send_order_update(db_order)
    if bar:
        user.transactions.append(
            Transaction(
                bar.id,
                bar.name,
                list(cart.items.values()),
                order_total,
                payment_method,
            )
        )
    cart.clear()
    save_cart_for_user(user.id, cart)
    return RedirectResponse(url="/orders", status_code=status.HTTP_303_SEE_OTHER)


# -----------------------------------------------------------------------------
# Orders
# -----------------------------------------------------------------------------


@app.get("/orders", response_class=HTMLResponse)
async def order_history(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    orders = (
        db.query(Order)
        .filter(Order.customer_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    pending_orders = [
        o for o in orders if o.status not in ("COMPLETED", "CANCELED", "REJECTED")
    ]
    completed_orders = [
        o for o in orders if o.status in ("COMPLETED", "CANCELED", "REJECTED")
    ]
    return render_template(
        "order_history.html",
        request=request,
        user=user,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        cart_bar_id=None,
        cart_bar_name=None,
    )


@app.get(
    "/api/bars/{bar_id}/orders",
    response_model=List[OrderWithItemsRead],
)
async def get_bar_orders(
    bar_id: int, request: Request, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    if (
        not user
        or (bar_id not in user.bar_ids and not user.is_super_admin)
        or not (user.is_bartender or user.is_bar_admin or user.is_super_admin)
    ):
        raise HTTPException(status_code=403, detail="Not authorised")
    orders = (
        db.query(Order)
        .filter(Order.bar_id == bar_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return orders


@app.post("/api/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = data.status.upper()
    allowed = ALLOWED_STATUS_TRANSITIONS.get(order.status, [])

    is_staff = bool(
        user
        and (
            user.is_super_admin
            or (
                order.bar_id in user.bar_ids
                and (user.is_bartender or user.is_bar_admin)
            )
        )
    )
    is_customer_cancel = (
        user
        and order.customer_id == user.id
        and order.status == "PLACED"
        and new_status == "CANCELED"
    )

    if not is_staff and not is_customer_cancel:
        raise HTTPException(status_code=403, detail="Not authorised")

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {order.status} -> {new_status}",
        )

    order.status = new_status
    now = datetime.utcnow()
    if new_status == "ACCEPTED" and not order.accepted_at:
        order.accepted_at = now
    if new_status == "READY" and not order.ready_at:
        order.ready_at = now
    if new_status == "CANCELED" and not order.cancelled_at:
        order.cancelled_at = now
        refund = Decimal(order.total)
        if order.payment_method in ("card", "wallet"):
            order.refund_amount = refund
            if order.customer_id:
                customer = db.get(User, order.customer_id)
                if customer:
                    customer.credit = Decimal(customer.credit or 0) + refund
                    cached = users.get(order.customer_id)
                    if cached:
                        cached.credit = float(customer.credit)
        else:
            order.refund_amount = Decimal("0")
    db.commit()
    order_data = await send_order_update(order)
    return {"status": order.status, "order": order_data}


@app.websocket("/ws/bar/{bar_id}/orders")
async def ws_bar_orders(websocket: WebSocket, bar_id: int):
    await order_ws_manager.connect_bar(bar_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        order_ws_manager.disconnect_bar(bar_id, websocket)


@app.websocket("/ws/user/{user_id}/orders")
async def ws_user_orders(websocket: WebSocket, user_id: int):
    await order_ws_manager.connect_user(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        order_ws_manager.disconnect_user(user_id, websocket)


# -----------------------------------------------------------------------------
# Wallet and credit management
# -----------------------------------------------------------------------------


@app.get("/wallet", response_class=HTMLResponse)
async def wallet(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "wallet.html",
        request=request,
        transactions=user.transactions,
        cart_bar_id=None,
        cart_bar_name=None,
    )


@app.get("/wallet/tx/{tx_id}", response_class=HTMLResponse)
async def wallet_transaction(request: Request, tx_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if tx_id < 0 or tx_id >= len(user.transactions):
        return RedirectResponse(url="/wallet", status_code=status.HTTP_303_SEE_OTHER)
    tx = user.transactions[tx_id]
    return render_template(
        "transaction_detail.html",
        request=request,
        tx=tx,
        cart_bar_id=None,
        cart_bar_name=None,
    )


@app.get("/topup", response_class=HTMLResponse)
async def topup(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    amount = request.query_params.get("amount")
    card = request.query_params.get("card")
    expiry = request.query_params.get("expiry")
    cvc = request.query_params.get("cvc")
    if amount and card and expiry and cvc:
        try:
            add_amount = float(amount)
            if add_amount <= 0:
                raise ValueError
        except ValueError:
            return render_template(
                "topup.html",
                request=request,
                error="Invalid amount",
                cart_bar_id=None,
                cart_bar_name=None,
            )
        # In a real application, integrate with a payment gateway here
        user.credit += add_amount
        db_user = db.query(User).filter(User.id == user.id).first()
        if db_user:
            db_user.credit = user.credit
            db.commit()
        return render_template(
            "topup.html",
            request=request,
            success=True,
            amount=add_amount,
            cart_bar_id=None,
            cart_bar_name=None,
        )
    return render_template(
        "topup.html", request=request, cart_bar_id=None, cart_bar_name=None
    )


# -----------------------------------------------------------------------------
# Authentication routes
# -----------------------------------------------------------------------------


@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    """Display the registration form."""
    return render_template("register.html", request=request)


@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, db: Session = Depends(get_db)):
    """Handle user registration submissions."""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    email = form.get("email")
    phone = form.get("phone")
    prefix = form.get("prefix")
    if all([username, password, email, phone, prefix]):
        if (
            username in users_by_username
            or db.query(User).filter(User.username == username).first()
        ):
            return render_template(
                "register.html", request=request, error="Username already taken"
            )
        if (
            email in users_by_email
            or db.query(User).filter(User.email == email).first()
        ):
            return render_template(
                "register.html", request=request, error="Email already taken"
            )
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        db_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            phone=phone,
            prefix=prefix,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        user = DemoUser(
            id=db_user.id,
            username=username,
            password=password,
            email=email,
            phone=phone,
            prefix=prefix,
        )
        users[user.id] = user
        users_by_username[user.username] = user
        users_by_email[user.email] = user
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "register.html", request=request, error="All fields are required"
    )


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """Display the login form."""
    return render_template("login.html", request=request)


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    """Handle login submissions."""
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    if email and password:
        user = users_by_email.get(email)
        if not user:
            db_user = db.query(User).filter(User.email == email).first()
            if db_user:
                expected = hashlib.sha256(password.encode("utf-8")).hexdigest()
                if db_user.password_hash == expected:
                    role_map = {
                        RoleEnum.SUPERADMIN: "super_admin",
                        RoleEnum.BARADMIN: "bar_admin",
                        RoleEnum.BARTENDER: "bartender",
                        RoleEnum.CUSTOMER: "customer",
                    }
                    bar_ids = [r.bar_id for r in db_user.bar_roles]
                    user = DemoUser(
                        id=db_user.id,
                        username=db_user.username,
                        password=password,
                        email=db_user.email,
                        phone=db_user.phone or "",
                        prefix=db_user.prefix or "",
                        role=role_map.get(db_user.role, "customer"),
                        bar_ids=bar_ids,
                        credit=float(db_user.credit or 0),
                    )
                    users[user.id] = user
                    users_by_email[user.email] = user
                    users_by_username[user.username] = user
        if not user or user.password != password:
            return render_template(
                "login.html", request=request, error="Invalid credentials"
            )
        request.session["user_id"] = user.id
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "login.html", request=request, error="Email and password required"
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if user.is_super_admin:
        return render_template("admin_dashboard.html", request=request)
    if user.is_bar_admin:
        bar_list = [bars.get(bid) for bid in user.bar_ids if bars.get(bid)]
        return render_template(
            "bar_admin_dashboard.html", request=request, bars=bar_list
        )
    if user.is_bartender:
        bar_list = [bars.get(bid) for bid in user.bar_ids if bars.get(bid)]
        return render_template(
            "bartender_dashboard.html", request=request, bars=bar_list
        )
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/dashboard/bar/{bar_id}/orders", response_class=HTMLResponse)
async def manage_orders(request: Request, bar_id: int):
    user = get_current_user(request)
    if (
        not user
        or (bar_id not in user.bar_ids and not user.is_super_admin)
        or not (user.is_bartender or user.is_bar_admin or user.is_super_admin)
    ):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404)
    template = "bar_admin_orders.html" if user.is_bar_admin or user.is_super_admin else "bartender_orders.html"
    return render_template(template, request=request, bar=bar)


@app.post("/dashboard/bar/{bar_id}/toggle_pause")
async def toggle_ordering_pause(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    if (
        not user
        or (bar_id not in user.bar_ids and not user.is_super_admin)
        or not (user.is_bartender or user.is_bar_admin or user.is_super_admin)
    ):
        raise HTTPException(status_code=403)
    data = await request.json()
    paused = bool(data.get("paused"))
    bar_model = db.get(BarModel, bar_id)
    if not bar_model:
        raise HTTPException(status_code=404)
    bar_model.ordering_paused = paused
    db.add(bar_model)
    db.commit()
    mem_bar = bars.get(bar_id)
    if mem_bar:
        mem_bar.ordering_paused = paused
    return {"ordering_paused": paused}


@app.get(
    "/dashboard/bar/{bar_id}/orders/history", response_class=HTMLResponse
)
async def bar_admin_order_history(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if (
        not user
        or (bar_id not in user.bar_ids and not user.is_super_admin)
        or not (user.is_bar_admin or user.is_super_admin)
    ):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404)
    closings = (
        db.query(BarClosing)
        .filter(BarClosing.bar_id == bar_id)
        .order_by(BarClosing.closed_at.desc())
        .all()
    )
    monthly_map: Dict[str, List[BarClosing]] = defaultdict(list)
    for c in closings:
        key = c.closed_at.strftime("%Y-%m")
        monthly_map[key].append(c)

    monthly = []
    now = datetime.now()
    current_year, current_month = now.year, now.month
    for key, clist in monthly_map.items():
        total = sum(Decimal(c.total_revenue or 0) for c in clist)
        commission = (total * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
        total_earned = (total - commission).quantize(Decimal("0.01"))
        payment_rows = (
            db.query(
                Order.payment_method,
                func.sum(Order.subtotal + Order.vat_total).label("amount"),
            )
            .filter(
                Order.bar_id == bar_id,
                Order.closing_id.in_([c.id for c in clist]),
                Order.status == "COMPLETED",
            )
            .group_by(Order.payment_method)
            .all()
        )
        payment_totals = {
            (pm or "Unknown").replace("_", " ").title(): float(
                Decimal(amount or 0).quantize(Decimal("0.01"))
            )
            for pm, amount in payment_rows
        }
        year, month = key.split("-")
        label = datetime(int(year), int(month), 1).strftime("%B %Y")
        is_past = int(year) < current_year or (
            int(year) == current_year and int(month) < current_month
        )
        confirmed = all(c.payment_confirmed for c in clist)
        monthly.append({
            "year": int(year),
            "month": int(month),
            "label": label,
            "total_revenue": float(total.quantize(Decimal("0.01"))),
            "siplygo_commission": float(commission),
            "total_earned": float(total_earned),
            "is_past": is_past,
            "confirmed": confirmed,
            "payment_totals": payment_totals,
        })

    monthly.sort(key=lambda m: (m["year"], m["month"]), reverse=True)

    return render_template(
        "bar_admin_order_history.html", request=request, bar=bar, monthly=monthly
    )


@app.get(
    "/dashboard/bar/{bar_id}/orders/history/{year}/{month}", response_class=HTMLResponse
)
async def bar_admin_order_history_month(
    request: Request, bar_id: int, year: int, month: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    if (
        not user
        or (bar_id not in user.bar_ids and not user.is_super_admin)
        or not (user.is_bar_admin or user.is_super_admin)
    ):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404)
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    closings = (
        db.query(BarClosing)
        .filter(
            BarClosing.bar_id == bar_id,
            BarClosing.closed_at >= start,
            BarClosing.closed_at < end,
        )
        .order_by(BarClosing.closed_at.desc())
        .all()
    )
    for c in closings:
        total = Decimal(c.total_revenue or 0)
        commission = (total * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
        c.siplygo_commission = float(commission)
        c.total_earned = float((total - commission).quantize(Decimal("0.01")))
        payment_rows = (
            db.query(
                Order.payment_method,
                func.sum(Order.subtotal + Order.vat_total).label("amount"),
            )
            .filter(
                Order.bar_id == bar_id,
                Order.closing_id == c.id,
                Order.status == "COMPLETED",
            )
            .group_by(Order.payment_method)
            .all()
        )
        c.payment_totals = {
            (pm or "Unknown").replace("_", " ").title(): float(
                Decimal(amount or 0).quantize(Decimal("0.01"))
            )
            for pm, amount in payment_rows
        }
    month_label = start.strftime("%B %Y")
    return render_template(
        "bar_admin_month_history.html",
        request=request,
        bar=bar,
        closings=closings,
        month_label=month_label,
    )


@app.post("/dashboard/bar/{bar_id}/orders/history/{year}/{month}/confirm")
async def confirm_monthly_payment(
    request: Request,
    bar_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    (
        db.query(BarClosing)
        .filter(
            BarClosing.bar_id == bar_id,
            BarClosing.closed_at >= start,
            BarClosing.closed_at < end,
        )
        .update({"payment_confirmed": True}, synchronize_session=False)
    )
    db.commit()
    return RedirectResponse(
        url=f"/dashboard/bar/{bar_id}/orders/history", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get(
    "/dashboard/bar/{bar_id}/orders/history/{closing_id}", response_class=HTMLResponse
)
async def bar_admin_order_history_view(
    request: Request, bar_id: int, closing_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    if (
        not user
        or (bar_id not in user.bar_ids and not user.is_super_admin)
        or not (user.is_bar_admin or user.is_super_admin)
    ):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404)
    closing = (
        db.query(BarClosing)
        .filter(BarClosing.id == closing_id, BarClosing.bar_id == bar_id)
        .first()
    )
    if not closing:
        raise HTTPException(status_code=404)
    orders = (
        db.query(Order)
        .filter(Order.bar_id == bar_id, Order.closing_id == closing_id)
        .order_by(Order.created_at.asc())
        .all()
    )
    total = Decimal(closing.total_revenue or 0)
    commission = (total * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
    closing.siplygo_commission = float(commission)
    closing.total_earned = float((total - commission).quantize(Decimal("0.01")))
    payment_totals: Dict[str, Decimal] = {}
    for o in orders:
        if o.status != "COMPLETED":
            continue
        method = (o.payment_method or "Unknown").replace("_", " ").title()
        amount = Decimal(o.subtotal or 0) + Decimal(o.vat_total or 0)
        payment_totals[method] = payment_totals.get(method, Decimal("0")) + amount
    payment_totals = {
        k: float(v.quantize(Decimal("0.01"))) for k, v in payment_totals.items()
    }
    return render_template(
        "bar_admin_order_history_view.html",
        request=request,
        bar=bar,
        closing=closing,
        orders=orders,
        payment_totals=payment_totals,
    )


# Admin management endpoints


@app.get("/admin/bars", response_class=HTMLResponse)
async def admin_bars_view(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    db_bars = db.query(BarModel).all()
    return render_template("admin_bars.html", request=request, bars=db_bars)


@app.get("/admin/bars/new", response_class=HTMLResponse)
async def new_bar_form(request: Request):
    """Display the creation form for a new bar."""
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "admin_new_bar.html",
        request=request,
        bar_categories=BAR_CATEGORIES,
    )


@app.post("/admin/bars/new")
async def create_bar_post(request: Request, db: Session = Depends(get_db)):
    """Create a new bar from submitted form data."""
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    address = form.get("address")
    city = form.get("city")
    state = form.get("state")
    latitude = form.get("latitude")
    longitude = form.get("longitude")
    description = form.get("description")
    if description:
        description = description[:120]
    rating = form.get("rating")
    manual_closed = form.get("manual_closed") == "on"
    hours = {}
    for i in range(7):
        o = form.get(f"open_{i}")
        c = form.get(f"close_{i}")
        if o and c:
            hours[str(i)] = {"open": o, "close": c}
    opening_hours = json.dumps(hours) if hours else None
    categories = form.getlist("categories")
    if len(categories) > 5:
        return render_template(
            "admin_new_bar.html",
            request=request,
            bar_categories=BAR_CATEGORIES,
            selected_categories=categories,
            error="Select up to 5 categories",
        )
    categories_csv = ",".join(categories) if categories else None
    photo_file = form.get("photo")
    photo_url = None
    if getattr(photo_file, "filename", None):
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        _, ext = os.path.splitext(photo_file.filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        photo_url = f"/static/uploads/{filename}"
    if not all([name, address, city, state, latitude, longitude, description]):
        return render_template(
            "admin_new_bar.html",
            request=request,
            bar_categories=BAR_CATEGORIES,
            selected_categories=categories,
            error="All fields are required",
        )
    try:
        lat = float(latitude)
        lon = float(longitude)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    db_bar = BarModel(
        name=name,
        slug=slugify(name),
        address=address,
        city=city,
        state=state,
        latitude=lat,
        longitude=lon,
        description=description,
        photo_url=photo_url,
        rating=float(rating) if rating else 0.0,
        is_open_now=is_open_now_from_hours(hours) and not manual_closed,
        opening_hours=opening_hours,
        manual_closed=manual_closed,
        bar_categories=categories_csv,
    )
    db.add(db_bar)
    db.commit()
    db.refresh(db_bar)
    bars[db_bar.id] = Bar(
        id=db_bar.id,
        name=name,
        address=address,
        city=city,
        state=state,
        latitude=lat,
        longitude=lon,
        description=description,
        photo_url=photo_url,
        rating=float(rating) if rating else 0.0,
        is_open_now=is_open_now_from_hours(hours) and not manual_closed,
        manual_closed=manual_closed,
        opening_hours=hours,
        bar_categories=categories,
    )
    return RedirectResponse(url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/bars/edit/{bar_id}", response_class=HTMLResponse)
async def edit_bar_options(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    """Display links to different bar management pages."""
    user = get_current_user(request)
    bar = db.get(BarModel, bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (
        user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids)
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_edit_bar_options.html", request=request, bar=bar)


@app.get("/admin/bars/edit/{bar_id}/info", response_class=HTMLResponse)
async def edit_bar_form(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    bar = db.get(BarModel, bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (
        user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids)
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    selected_categories = bar.bar_categories.split(",") if bar.bar_categories else []
    try:
        hours = json.loads(bar.opening_hours) if bar.opening_hours else {}
        if not isinstance(hours, dict):
            hours = {}
    except Exception:
        hours = {}
    return render_template(
        "admin_edit_bar.html",
        request=request,
        bar=bar,
        hours=hours,
        bar_categories=BAR_CATEGORIES,
        selected_categories=selected_categories,
    )


@app.post("/admin/bars/edit/{bar_id}/info")
async def edit_bar_post(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    bar = db.get(BarModel, bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (
        user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids)
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    address = form.get("address")
    city = form.get("city")
    state = form.get("state")
    latitude = form.get("latitude")
    longitude = form.get("longitude")
    description = form.get("description")
    if description:
        description = description[:120]
    rating = form.get("rating")
    manual_closed = form.get("manual_closed") == "on"
    hours = {}
    for i in range(7):
        o = form.get(f"open_{i}")
        c = form.get(f"close_{i}")
        if o and c:
            hours[str(i)] = {"open": o, "close": c}
    opening_hours = json.dumps(hours) if hours else None
    categories = form.getlist("categories")
    if len(categories) > 5:
        return render_template(
            "admin_edit_bar.html",
            request=request,
            bar=bar,
            hours=hours,
            bar_categories=BAR_CATEGORIES,
            selected_categories=categories,
            error="Select up to 5 categories",
        )
    categories_csv = ",".join(categories) if categories else None
    photo_file = form.get("photo")
    photo_url = bar.photo_url
    if getattr(photo_file, "filename", None):
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        _, ext = os.path.splitext(photo_file.filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        photo_url = f"/static/uploads/{filename}"
    if all([name, address, city, state, latitude, longitude, description]):
        try:
            lat = float(latitude)
            lon = float(longitude)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid coordinates")
        bar.name = name
        bar.address = address
        bar.city = city
        bar.state = state
        bar.latitude = lat
        bar.longitude = lon
        bar.description = description
        bar.photo_url = photo_url
        bar.rating = float(rating) if rating else 0.0
        bar.opening_hours = opening_hours
        bar.manual_closed = manual_closed
        bar.is_open_now = is_open_now_from_hours(hours) and not manual_closed
        bar.bar_categories = categories_csv
        db.commit()
        mem_bar = bars.get(bar_id)
        if mem_bar:
            mem_bar.name = name
            mem_bar.address = address
            mem_bar.city = city
            mem_bar.state = state
            mem_bar.latitude = lat
            mem_bar.longitude = lon
            mem_bar.description = description
            mem_bar.photo_url = photo_url
            mem_bar.rating = float(rating) if rating else 0.0
            mem_bar.opening_hours = hours
            mem_bar.manual_closed = manual_closed
            mem_bar.is_open_now = is_open_now_from_hours(hours) and not manual_closed
            mem_bar.bar_categories = categories
        if user.is_super_admin:
            return RedirectResponse(
                url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER
            )
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "admin_edit_bar.html",
        request=request,
        bar=bar,
        hours=hours,
        bar_categories=BAR_CATEGORIES,
        selected_categories=categories,
        error="All fields are required",
    )


@app.post("/admin/bars/{bar_id}/delete")
async def delete_bar(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    bar = db.get(BarModel, bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    # Remove dependent records to satisfy foreign key constraints
    menu_item_ids = [
        m.id for m in db.query(MenuItem.id).filter(MenuItem.bar_id == bar_id)
    ]
    if menu_item_ids:
        db.query(MenuVariant).filter(
            MenuVariant.menu_item_id.in_(menu_item_ids)
        ).delete(synchronize_session=False)
    db.query(MenuItem).filter(MenuItem.bar_id == bar_id).delete(
        synchronize_session=False
    )

    db.query(CategoryModel).filter(CategoryModel.bar_id == bar_id).delete(
        synchronize_session=False
    )
    db.query(UserBarRole).filter(UserBarRole.bar_id == bar_id).delete(
        synchronize_session=False
    )

    order_ids = [o.id for o in db.query(Order.id).filter(Order.bar_id == bar_id)]
    if order_ids:
        db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
    db.query(Order).filter(Order.bar_id == bar_id).delete(synchronize_session=False)

    db.query(Payout).filter(Payout.bar_id == bar_id).delete(synchronize_session=False)

    db.delete(bar)
    db.commit()
    bars.pop(bar_id, None)
    return RedirectResponse(url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/bars/{bar_id}/users", response_class=HTMLResponse)
async def manage_bar_users(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not user
        or not (user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    staff = [_load_demo_user(uid, db) for uid in bar.bar_admin_ids + bar.bartender_ids]
    return render_template(
        "admin_bar_users.html", request=request, bar=bar, staff=staff
    )


@app.post("/admin/bars/{bar_id}/users", response_class=HTMLResponse)
async def manage_bar_users_post(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    current = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not current
        or not (
            current.is_super_admin
            or (current.is_bar_admin and bar_id in current.bar_ids)
        )
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    action = form.get("action")
    role = form.get("role")
    role_map = {"bar_admin": RoleEnum.BARADMIN, "bartender": RoleEnum.BARTENDER}
    error = None
    message = None
    if action == "existing":
        email = form.get("email")
        if not email or role not in role_map:
            error = "Email and role required"
        else:
            db_user = db.query(User).filter(User.email == email).first()
            if not db_user:
                error = "User not found"
            else:
                db_user.role = role_map[role]
                rel = (
                    db.query(UserBarRole)
                    .filter(
                        UserBarRole.user_id == db_user.id,
                        UserBarRole.bar_id == bar_id,
                    )
                    .first()
                )
                if not rel:
                    rel = UserBarRole(
                        user_id=db_user.id, bar_id=bar_id, role=role_map[role]
                    )
                    db.add(rel)
                else:
                    rel.role = role_map[role]
                db.commit()
                demo = _load_demo_user(db_user.id, db)
                demo.role = role
                if bar_id not in demo.bar_ids:
                    demo.bar_ids.append(bar_id)
                if role == "bar_admin":
                    if demo.id not in bar.bar_admin_ids:
                        bar.bar_admin_ids.append(demo.id)
                    if demo.id in bar.bartender_ids:
                        bar.bartender_ids.remove(demo.id)
                else:
                    if demo.id not in bar.bartender_ids:
                        bar.bartender_ids.append(demo.id)
                    if demo.id in bar.bar_admin_ids:
                        bar.bar_admin_ids.remove(demo.id)
                message = "User assigned"
    elif action == "new":
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        phone = form.get("phone")
        prefix = form.get("prefix")
        if not all([username, email, password, phone, prefix]) or role not in role_map:
            error = "All fields are required"
        elif (
            username in users_by_username
            or db.query(User).filter(User.username == username).first()
        ):
            error = "Username already taken"
        elif (
            email in users_by_email
            or db.query(User).filter(User.email == email).first()
        ):
            error = "Email already taken"
        else:
            password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            db_user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                phone=phone,
                prefix=prefix,
                role=role_map[role],
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            db_role = UserBarRole(
                user_id=db_user.id, bar_id=bar_id, role=role_map[role]
            )
            db.add(db_role)
            db.commit()
            demo = DemoUser(
                id=db_user.id,
                username=username,
                password=password,
                email=email,
                phone=phone,
                prefix=prefix,
                role=role,
                bar_ids=[bar_id],
            )
            users[demo.id] = demo
            users_by_username[demo.username] = demo
            users_by_email[demo.email] = demo
            if role == "bar_admin":
                bar.bar_admin_ids.append(demo.id)
            else:
                bar.bartender_ids.append(demo.id)
            message = "User created"
    staff = [_load_demo_user(uid, db) for uid in bar.bar_admin_ids + bar.bartender_ids]
    return render_template(
        "admin_bar_users.html",
        request=request,
        bar=bar,
        staff=staff,
        error=error,
        message=message,
    )


@app.get("/admin/bars/{bar_id}/tables", response_class=HTMLResponse)
async def manage_bar_tables(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not user
        or not (user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    tables = sorted(bar.tables.values(), key=lambda t: t.id)
    return render_template(
        "admin_bar_tables.html", request=request, bar=bar, tables=tables
    )


@app.get("/admin/bars/{bar_id}/tables/new", response_class=HTMLResponse)
async def new_bar_table_form(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not user
        or not (user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_bar_new_table.html", request=request, bar=bar)


@app.post("/admin/bars/{bar_id}/tables/new")
async def add_bar_table(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not user
        or not (user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    description = form.get("description")
    if not name:
        return RedirectResponse(
            url=f"/admin/bars/{bar_id}/tables",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    table = TableModel(bar_id=bar_id, name=name, description=description)
    db.add(table)
    db.commit()
    db.refresh(table)
    bar.tables[table.id] = Table(id=table.id, name=name, description=description or "")
    return RedirectResponse(
        url=f"/admin/bars/{bar_id}/tables",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/admin/bars/{bar_id}/tables/{table_id}/edit", response_class=HTMLResponse)
async def edit_bar_table_form(
    request: Request, bar_id: int, table_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not user
        or not (user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    table = bar.tables.get(table_id)
    if not table:
        return RedirectResponse(
            url=f"/admin/bars/{bar_id}/tables",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return render_template(
        "admin_bar_edit_table.html", request=request, bar=bar, table=table
    )


@app.post("/admin/bars/{bar_id}/tables/{table_id}/edit")
async def edit_bar_table(
    request: Request, bar_id: int, table_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not user
        or not (user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    db_table = db.get(TableModel, table_id)
    if not db_table or db_table.bar_id != bar_id:
        return RedirectResponse(
            url=f"/admin/bars/{bar_id}/tables",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    form = await request.form()
    name = form.get("name")
    description = form.get("description")
    if not name:
        return RedirectResponse(
            url=f"/admin/bars/{bar_id}/tables/{table_id}/edit",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    db_table.name = name
    db_table.description = description
    db.commit()
    db.refresh(db_table)
    bar.tables[table_id] = Table(
        id=db_table.id, name=db_table.name, description=db_table.description or ""
    )
    return RedirectResponse(
        url=f"/admin/bars/{bar_id}/tables",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/admin/bars/{bar_id}/tables/{table_id}/delete")
async def delete_bar_table(
    request: Request, bar_id: int, table_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if (
        not bar
        or not user
        or not (user.is_super_admin or (user.is_bar_admin and bar_id in user.bar_ids))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    db_table = db.get(TableModel, table_id)
    if db_table and db_table.bar_id == bar_id:
        db.delete(db_table)
        db.commit()
        bar.tables.pop(table_id, None)
    return RedirectResponse(
        url=f"/admin/bars/{bar_id}/tables",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/confirm_bartender", response_class=HTMLResponse)
async def confirm_bartender(request: Request):
    user = get_current_user(request)
    try:
        bar_id = int(request.query_params.get("bar_id", 0))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bar")
    bar = bars.get(bar_id)
    if not user or not bar or user.pending_bar_id != bar_id:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    user.role = "bartender"
    if bar_id not in user.bar_ids:
        user.bar_ids.append(bar_id)
    user.pending_bar_id = None
    if user.id not in bar.bartender_ids:
        bar.bartender_ids.append(user.id)
    if user.id in bar.pending_bartender_ids:
        bar.pending_bartender_ids.remove(user.id)
    return render_template("bartender_confirm.html", request=request, bar=bar)


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_dashboard.html", request=request)


@app.get("/admin/payments", response_class=HTMLResponse)
async def admin_payments(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    db_bars = db.query(BarModel).all()
    return render_template("admin_payments.html", request=request, bars=db_bars)


@app.post("/admin/payments/{bar_id}/test_closing")
async def admin_create_test_closing(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    now = datetime.now()
    if now.month == 1:
        year = now.year - 1
        month = 12
    else:
        year = now.year
        month = now.month - 1
    start = datetime(year, month, 1)
    closing = BarClosing(bar_id=bar_id, closed_at=start, total_revenue=0)
    db.add(closing)
    db.commit()
    return RedirectResponse(
        url=f"/dashboard/bar/{bar_id}/orders/history",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/admin/payments/{bar_id}/test_closing/delete")
async def admin_delete_test_closing(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    now = datetime.now()
    if now.month == 1:
        year = now.year - 1
        month = 12
    else:
        year = now.year
        month = now.month - 1
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    (
        db.query(BarClosing)
        .filter(
            BarClosing.bar_id == bar_id,
            BarClosing.closed_at >= start,
            BarClosing.closed_at < end,
            BarClosing.total_revenue == 0,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return RedirectResponse(
        url=f"/dashboard/bar/{bar_id}/orders/history",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/admin/orders/clear")
async def admin_clear_orders(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    gmv_gross = float(
        db.query(func.coalesce(func.sum(Order.subtotal + Order.vat_total), 0)).scalar()
    )
    commission_amount = float(
        db.query(func.coalesce(func.sum(Order.fee_platform_5pct), 0)).scalar()
    )
    payout_total = float(
        db.query(func.coalesce(func.sum(Order.payout_due_to_bar), 0)).scalar()
    )
    cancelled_orders = (
        db.query(func.count(Order.id)).filter(Order.status == "cancelled").scalar() or 0
    )
    gmv_net = gmv_gross
    aov = gmv_gross / total_orders if total_orders else 0
    commission_pct = (commission_amount / gmv_gross * 100) if gmv_gross else 0
    cancellation_rate = cancelled_orders / total_orders * 100 if total_orders else 0

    daily = (
        db.query(
            func.date(Order.created_at).label("day"),
            func.sum(Order.subtotal + Order.vat_total).label("gmv"),
            func.count(Order.id).label("orders"),
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    daily_labels = [d.day.strftime("%Y-%m-%d") for d in daily]
    daily_gmv = [float(d.gmv) for d in daily]
    daily_orders = [d.orders for d in daily]

    peak = (
        db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("cnt"),
        )
        .group_by("hour")
        .order_by(func.count(Order.id).desc())
        .first()
    )
    peak_hour = f"{int(peak.hour):02d}" if peak else "N/A"

    top_bar = (
        db.query(BarModel.name, func.count(Order.id).label("cnt"))
        .join(Order, BarModel.id == Order.bar_id)
        .group_by(BarModel.id)
        .order_by(func.count(Order.id).desc())
        .first()
    )
    top_bar_name = top_bar.name if top_bar else "N/A"

    top_category = (
        db.query(CategoryModel.name, func.sum(OrderItem.qty).label("qty"))
        .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
        .join(CategoryModel, CategoryModel.id == MenuItem.category_id)
        .group_by(CategoryModel.id)
        .order_by(func.sum(OrderItem.qty).desc())
        .first()
    )
    top_category_name = top_category.name if top_category else "N/A"

    revenue_rows = (
        db.query(
            BarModel.name.label("bar"),
            func.sum(Order.subtotal + Order.vat_total).label("gmv"),
            func.sum(Order.vat_total).label("vat"),
            func.sum(Order.fee_platform_5pct).label("commission"),
            func.sum(Order.payout_due_to_bar).label("net"),
        )
        .join(BarModel, BarModel.id == Order.bar_id)
        .group_by(BarModel.id)
        .all()
    )
    revenue_bars = []
    for row in revenue_rows:
        gmv = float(row.gmv or 0)
        commission = float(row.commission or 0)
        revenue_bars.append(
            {
                "bar": row.bar,
                "gmv": gmv,
                "vat": float(row.vat or 0),
                "commission": commission,
                "net": float(row.net or 0),
                "take_rate": (commission / gmv * 100) if gmv else 0,
            }
        )

    hourly = (
        db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("cnt"),
        )
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    hourly_labels = [f"{int(h.hour):02d}" for h in hourly]
    hourly_orders = [h.cnt for h in hourly]

    top_products = (
        db.query(
            MenuItem.name.label("name"),
            func.sum(OrderItem.qty).label("qty"),
            func.sum(OrderItem.line_total).label("revenue"),
        )
        .join(OrderItem, MenuItem.id == OrderItem.menu_item_id)
        .group_by(MenuItem.id)
        .order_by(func.sum(OrderItem.qty).desc())
        .limit(5)
        .all()
    )
    product_rows = [
        {
            "name": p.name,
            "qty": int(p.qty or 0),
            "revenue": float(p.revenue or 0),
        }
        for p in top_products
    ]

    customer_rows = (
        db.query(
            Order.customer_id.label("cid"),
            func.count(Order.id).label("cnt"),
            func.sum(Order.subtotal + Order.vat_total).label("spend"),
            func.max(Order.created_at).label("last"),
        )
        .filter(Order.customer_id.isnot(None))
        .group_by(Order.customer_id)
        .all()
    )
    new_customers = sum(1 for c in customer_rows if c.cnt == 1)
    returning_customers = sum(1 for c in customer_rows if c.cnt > 1)
    customers = [
        {
            "id": f"C{c.cid}",
            "count": int(c.cnt),
            "spend": float(c.spend or 0),
            "last": c.last.strftime("%Y-%m-%d") if c.last else "",
        }
        for c in customer_rows
    ]

    payouts = [
        {
            "start": p.period_start.strftime("%Y-%m-%d"),
            "end": p.period_end.strftime("%Y-%m-%d"),
            "amount": float(p.amount_chf),
            "status": p.status,
        }
        for p in db.query(Payout).all()
    ]

    refund_total = float(
        db.query(func.coalesce(func.sum(Order.refund_amount), 0)).scalar()
    )
    refund_count = (
        db.query(func.count(Order.id)).filter(Order.refund_amount > 0).scalar() or 0
    )
    vat_total = float(db.query(func.coalesce(func.sum(Order.vat_total), 0)).scalar())

    stats = {
        "users": db.query(User).count(),
        "bars": db.query(BarModel).count(),
        "orders": total_orders,
        "gmv_gross": gmv_gross,
        "gmv_net": gmv_net,
        "aov": aov,
        "commission_amount": commission_amount,
        "commission_pct": commission_pct,
        "payout_total": payout_total,
        "tips": 0.0,
        "cancellation_rate": cancellation_rate,
        "cancelled_orders": cancelled_orders,
        "daily_labels": daily_labels,
        "daily_gmv": daily_gmv,
        "daily_orders": daily_orders,
        "peak_hour": peak_hour,
        "top_bar": top_bar_name,
        "top_category": top_category_name,
        "revenue_bars": revenue_bars,
        "hourly_labels": hourly_labels,
        "hourly_orders": hourly_orders,
        "top_products": product_rows,
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "customers": customers,
        "payouts": payouts,
        "refund_total": refund_total,
        "refund_count": refund_count,
        "vat_total": vat_total,
    }
    return render_template("admin_analytics.html", request=request, stats=stats)


@app.get("/admin/profile", response_class=HTMLResponse)
async def admin_profile(request: Request):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_profile.html", request=request)


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_view(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    # Synchronise in-memory users with the database so the list is always
    # up to date even after a restart.
    db_users = db.query(User).all()
    role_map = {
        RoleEnum.SUPERADMIN: "super_admin",
        RoleEnum.BARADMIN: "bar_admin",
        RoleEnum.BARTENDER: "bartender",
        RoleEnum.CUSTOMER: "customer",
    }
    for db_user in db_users:
        existing = users.get(db_user.id)
        bar_ids = [r.bar_id for r in db_user.bar_roles]
        credit = float(db_user.credit or 0)
        if existing:
            existing.username = db_user.username
            existing.email = db_user.email
            existing.phone = db_user.phone or ""
            existing.prefix = db_user.prefix or ""
            existing.role = role_map.get(db_user.role, "customer")
            existing.bar_ids = bar_ids
            existing.credit = credit
        else:
            demo = DemoUser(
                id=db_user.id,
                username=db_user.username,
                password="",
                email=db_user.email,
                phone=db_user.phone or "",
                prefix=db_user.prefix or "",
                role=role_map.get(db_user.role, "customer"),
                bar_ids=bar_ids,
                credit=credit,
            )
            users[demo.id] = demo
            users_by_username[demo.username] = demo
            users_by_email[demo.email] = demo
    return render_template(
        "admin_users.html",
        request=request,
        user=user,
        users=users.values(),
        bars=bars,
    )


def _load_demo_user(user_id: int, db: Session) -> DemoUser:
    """Ensure a DemoUser exists for the given user id."""
    user = users.get(user_id)
    if user:
        return user
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    role_map = {
        RoleEnum.SUPERADMIN: "super_admin",
        RoleEnum.BARADMIN: "bar_admin",
        RoleEnum.BARTENDER: "bartender",
        RoleEnum.CUSTOMER: "customer",
    }
    bar_ids = [r.bar_id for r in db_user.bar_roles]
    user = DemoUser(
        id=db_user.id,
        username=db_user.username,
        password="",
        email=db_user.email,
        phone=db_user.phone or "",
        prefix=db_user.prefix or "",
        role=role_map.get(db_user.role, "customer"),
        bar_ids=bar_ids,
        credit=float(db_user.credit or 0),
    )
    users[user.id] = user
    users_by_username[user.username] = user
    users_by_email[user.email] = user
    return user


@app.get("/admin/users/edit/{user_id}", response_class=HTMLResponse)
async def edit_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    current = get_current_user(request)
    if not current:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    user = _load_demo_user(user_id, db)
    if not (
        current.is_super_admin
        or (
            current.is_bar_admin
            and any(bid in current.bar_ids for bid in user.bar_ids)
        )
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "admin_edit_user.html",
        request=request,
        user=user,
        bars=bars.values(),
        current=current,
    )


@app.post("/admin/users/edit/{user_id}", response_class=HTMLResponse)
async def update_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    current = get_current_user(request)
    if not current:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    user = _load_demo_user(user_id, db)
    if not (
        current.is_super_admin
        or (
            current.is_bar_admin
            and any(bid in current.bar_ids for bid in user.bar_ids)
        )
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    email = form.get("email")
    prefix = form.get("prefix")
    phone = form.get("phone")
    role = form.get("role")
    credit = form.get("credit")
    bar_ids = [int(b) for b in form.getlist("bar_ids") if b]
    if not (username and email is not None and role is not None):
        return render_template(
            "admin_edit_user.html",
            request=request,
            user=user,
            bars=bars.values(),
            current=current,
        )
    if username != user.username and (
        username in users_by_username
        or db.query(User).filter(User.username == username).first()
    ):
        return render_template(
            "admin_edit_user.html",
            request=request,
            user=user,
            bars=bars.values(),
            current=current,
            error="Username already taken",
        )
    if email != user.email and (
        email in users_by_email or db.query(User).filter(User.email == email).first()
    ):
        return render_template(
            "admin_edit_user.html",
            request=request,
            user=user,
            bars=bars.values(),
            current=current,
            error="Email already taken",
        )
    if username != user.username:
        del users_by_username[user.username]
        user.username = username
        users_by_username[user.username] = user
    if email != user.email:
        del users_by_email[user.email]
        user.email = email
        users_by_email[user.email] = user
    else:
        user.email = email
    if password:
        user.password = password
    user.prefix = prefix or ""
    user.phone = phone or ""
    if not current.is_super_admin:
        role = "bar_admin" if role == "bar_admin" else "bartender"
        bar_ids = current.bar_ids.copy()
        credit = str(user.credit)
    user.role = role
    user.bar_ids = bar_ids
    try:
        user.credit = float(credit)
    except (TypeError, ValueError):
        return render_template(
            "admin_edit_user.html",
            request=request,
            user=user,
            bars=bars.values(),
            current=current,
            error="Invalid credit amount",
        )
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = username
    db_user.email = email
    db_user.prefix = prefix or None
    db_user.phone = phone or None
    if password:
        db_user.password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    role_enum_map = {
        "super_admin": RoleEnum.SUPERADMIN,
        "bar_admin": RoleEnum.BARADMIN,
        "bartender": RoleEnum.BARTENDER,
        "customer": RoleEnum.CUSTOMER,
    }
    role_enum = role_enum_map.get(role, RoleEnum.CUSTOMER)
    db_user.role = role_enum
    db_user.credit = Decimal(str(user.credit))
    # Update user-bar role association: remove previous roles then add new assignment
    db.query(UserBarRole).filter(UserBarRole.user_id == user_id).delete(
        synchronize_session=False
    )
    db.flush()
    for bid in user.bar_ids:
        db.add(
            UserBarRole(
                user_id=user_id,
                bar_id=bid,
                role=role_enum,
            )
        )
    db.commit()
    # Update in-memory user caches to reflect new data
    users[user.id] = user
    users_by_username[user.username] = user
    users_by_email[user.email] = user
    # Update in-memory bar assignments
    for b in bars.values():
        if user_id in b.bar_admin_ids:
            b.bar_admin_ids.remove(user_id)
        if user_id in b.bartender_ids:
            b.bartender_ids.remove(user_id)
    for bid in user.bar_ids:
        target = bars.get(bid) or refresh_bar_from_db(bid, db)
        if role == "bar_admin":
            if user_id not in target.bar_admin_ids:
                target.bar_admin_ids.append(user_id)
        elif role == "bartender":
            if user_id not in target.bartender_ids:
                target.bartender_ids.append(user_id)
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/bar/{bar_id}/categories", response_class=HTMLResponse)
async def bar_manage_categories(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    categories = sorted(bar.categories.values(), key=lambda c: c.display_order)
    return render_template(
        "bar_manage_categories.html",
        request=request,
        bar=bar,
        categories=categories,
    )


@app.get("/bar/{bar_id}/categories/new", response_class=HTMLResponse)
async def bar_new_category_form(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("bar_new_category.html", request=request, bar=bar)


@app.post("/bar/{bar_id}/categories/new")
async def bar_new_category(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    description = form.get("description")
    display_order = form.get("display_order") or 0
    if not name or not description:
        return render_template(
            "bar_new_category.html",
            request=request,
            bar=bar,
            error="Name and description are required",
        )
    try:
        order_val = int(display_order)
    except ValueError:
        order_val = 0
    db_category = CategoryModel(
        bar_id=bar_id,
        name=name,
        description=description,
        sort_order=order_val,
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    category = Category(
        id=db_category.id,
        name=name,
        description=description,
        display_order=order_val,
    )
    bar.categories[category.id] = category
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories", status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/bar/{bar_id}/categories/{category_id}/delete")
async def bar_delete_category(
    request: Request, bar_id: int, category_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    db.query(MenuItem).filter(MenuItem.category_id == category_id).delete(
        synchronize_session=False
    )
    db.query(CategoryModel).filter(CategoryModel.id == category_id).delete(
        synchronize_session=False
    )
    db.commit()
    bar.categories.pop(category_id, None)
    bar.products = {
        pid: p for pid, p in bar.products.items() if p.category_id != category_id
    }
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/bar/{bar_id}/categories/{category_id}/products", response_class=HTMLResponse)
async def bar_category_products(
    request: Request, bar_id: int, category_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    products = sorted(
        [p for p in bar.products.values() if p.category_id == category_id],
        key=lambda p: p.display_order,
    )
    for p in products:
        p.photo_url = make_absolute_url(p.photo_url, request)
    return render_template(
        "bar_category_products.html",
        request=request,
        bar=bar,
        category=category,
        products=products,
    )


@app.get(
    "/bar/{bar_id}/categories/{category_id}/products/new",
    response_class=HTMLResponse,
)
async def bar_new_product_form(
    request: Request, bar_id: int, category_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "bar_new_product.html", request=request, bar=bar, category=category
    )


@app.post("/bar/{bar_id}/categories/{category_id}/products/new")
async def bar_new_product(
    request: Request, bar_id: int, category_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    price = form.get("price")
    description = form.get("description")
    if description:
        description = description[:190]
    display_order = form.get("display_order") or 0
    photo_file = form.get("photo")
    photo_url = await save_upload(photo_file)
    if not name or not description or not price:
        return render_template(
            "bar_new_product.html",
            request=request,
            bar=bar,
            category=category,
            error="All fields are required",
        )
    try:
        price_val = float(price)
        price_decimal = Decimal(price)
    except ValueError:
        return render_template(
            "bar_new_product.html",
            request=request,
            bar=bar,
            category=category,
            error="Invalid price",
        )
    try:
        order_val = int(display_order)
    except ValueError:
        order_val = 0
    db_item = MenuItem(
        bar_id=bar_id,
        category_id=category_id,
        name=name,
        description=description,
        price_chf=price_decimal,
        photo=photo_url,
        sort_order=order_val,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    refresh_bar_from_db(bar_id, db)
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories/{category_id}/products",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/bar/{bar_id}/categories/{category_id}/products/{product_id}/delete")
async def bar_delete_product(
    request: Request,
    bar_id: int,
    category_id: int,
    product_id: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    product = bar.products.get(product_id)
    if not product or product.category_id != category_id:
        raise HTTPException(status_code=404, detail="Product not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    db.query(MenuItem).filter(MenuItem.id == product_id).delete()
    db.commit()
    bar.products.pop(product_id, None)
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories/{category_id}/products",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get(
    "/bar/{bar_id}/categories/{category_id}/products/{product_id}/edit",
    response_class=HTMLResponse,
)
async def bar_edit_product_form(
    request: Request,
    bar_id: int,
    category_id: int,
    product_id: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    db_item = db.get(MenuItem, product_id)
    if not category or not db_item or db_item.category_id != category_id:
        raise HTTPException(status_code=404, detail="Product not found")
    product = Product(
        id=db_item.id,
        category_id=db_item.category_id,
        name=db_item.name,
        price=float(db_item.price_chf),
        description=db_item.description or "",
        display_order=db_item.sort_order or 0,
        photo_url=make_absolute_url(f"/api/products/{db_item.id}/image", request),
    )
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "bar_edit_product.html",
        request=request,
        bar=bar,
        category=category,
        product=product,
    )


@app.post("/bar/{bar_id}/categories/{category_id}/products/{product_id}/edit")
async def bar_edit_product(
    request: Request,
    bar_id: int,
    category_id: int,
    product_id: int,
    db: Session = Depends(get_db),
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    db_item = db.get(MenuItem, product_id)
    if not category or not db_item or db_item.category_id != category_id:
        raise HTTPException(status_code=404, detail="Product not found")
    product = bar.products.get(product_id)
    if not product:
        product = Product(
            id=db_item.id,
            category_id=db_item.category_id,
            name=db_item.name,
            price=float(db_item.price_chf),
            description=db_item.description or "",
            display_order=db_item.sort_order or 0,
            photo_url=f"/api/products/{db_item.id}/image",
        )
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    price = form.get("price")
    description = form.get("description")
    if description:
        description = description[:190]
    display_order = form.get("display_order") or product.display_order
    photo_file = form.get("photo")
    if name:
        product.name = db_item.name = name
    if description:
        product.description = db_item.description = description
    if price:
        try:
            price_val = float(price)
            price_dec = Decimal(price)
            product.price = price_val
            db_item.price_chf = price_dec
        except ValueError:
            pass
    try:
        order_val = int(display_order)
        product.display_order = order_val
        db_item.sort_order = order_val
    except ValueError:
        pass
    if getattr(photo_file, "filename", ""):
        data = await photo_file.read()
        mime = photo_file.content_type or ""
        if mime.startswith("image/") and len(data) <= 5 * 1024 * 1024:
            img = db.query(ProductImage).filter_by(product_id=db_item.id).first()
            if img:
                img.data = data
                img.mime = mime
            else:
                db.add(ProductImage(product_id=db_item.id, data=data, mime=mime))
        await photo_file.close()
    product.photo_url = f"/api/products/{db_item.id}/image"
    db_item.photo = None
    db.commit()
    db.refresh(db_item)
    refresh_bar_from_db(bar_id, db)
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories/{category_id}/products",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/bar/{bar_id}/categories/{category_id}/edit", response_class=HTMLResponse)
async def bar_edit_category_form(
    request: Request, bar_id: int, category_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "bar_edit_category.html", request=request, bar=bar, category=category
    )


@app.post("/bar/{bar_id}/categories/{category_id}/edit")
async def bar_edit_category(
    request: Request, bar_id: int, category_id: int, db: Session = Depends(get_db)
):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    category = bar.categories.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not user or not (
        user.is_super_admin
        or (bar_id in user.bar_ids and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    description = form.get("description")
    display_order = form.get("display_order") or category.display_order
    db_category = db.get(CategoryModel, category_id)
    if name:
        category.name = name
        if db_category:
            db_category.name = name
    if description:
        category.description = description
        if db_category:
            db_category.description = description
    try:
        order_val = int(display_order)
        category.display_order = order_val
        if db_category:
            db_category.sort_order = order_val
    except ValueError:
        pass
    if db_category:
        db.commit()
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories", status_code=status.HTTP_303_SEE_OTHER
    )
