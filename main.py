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
import hashlib
import json
import random
from typing import Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request, status, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
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
    User,
    RoleEnum,
    UserBarRole,
    Category as CategoryModel,
)
from pydantic import BaseModel
from decimal import Decimal
from finance import (
    calculate_platform_fee,
    calculate_payout,
    calculate_vat_from_gross,
)
from payouts import schedule_payout
from audit import log_action
from urllib.parse import urljoin

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
        self.description = description
        self.display_order = display_order
        self.photo_url = photo_url


class Table:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


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
        opening_hours: Optional[Dict[str, Dict[str, str]]] = None,
        promo_label: Optional[str] = None,
        tags: Optional[List[str]] = None,
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
        self.opening_hours = opening_hours or {}
        self.promo_label = promo_label
        self.tags = tags or []
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
        bar_id: Optional[int] = None,
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
        self.bar_id = bar_id
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
    def __init__(self, bar_id: int, bar_name: str, items: List[CartItem], total: float):
        self.bar_id = bar_id
        self.bar_name = bar_name
        self.items = [
            TransactionItem(item.product.name, item.quantity, item.product.price)
            for item in items
        ]
        self.total = total


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
        "promo_label": "VARCHAR(100)",
        "tags": "TEXT",
        "opening_hours": "TEXT",
    }
    missing = {name: ddl for name, ddl in required.items() if name not in columns}
    if missing:
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(text(f"ALTER TABLE bars ADD COLUMN IF NOT EXISTS {name} {ddl}"))


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
    required = {"sort_order": "INTEGER"}
    missing = {name: ddl for name, ddl in required.items() if name not in columns}
    if missing:
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(
                    text(
                        f"ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS {name} {ddl}"
                    )
                )


@app.on_event("startup")
def on_startup():
    """Initialise database tables on startup."""
    Base.metadata.create_all(bind=engine)
    ensure_prefix_column()
    ensure_bar_columns()
    ensure_category_columns()
    ensure_menu_item_columns()
    seed_super_admin()
    load_bars_from_db()

# Jinja2 environment for rendering HTML templates
templates_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# -----------------------------------------------------------------------------
# In-memory store with sample data
# -----------------------------------------------------------------------------

bars: Dict[int, Bar] = {}
next_table_id = 1

# User storage
users: Dict[int, DemoUser] = {}
users_by_username: Dict[str, DemoUser] = {}
users_by_email: Dict[str, DemoUser] = {}
next_user_id = 1

# Cart storage per user
user_carts: Dict[int, Cart] = {}



# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def get_current_user(request: Request) -> Optional[DemoUser]:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return users.get(user_id)


def get_cart_for_user(user: DemoUser) -> Cart:
    return user_carts.setdefault(user.id, Cart())


def slugify(value: str) -> str:
    """Convert a string to a simple slug."""
    return value.lower().replace(" ", "-")


def is_open_now_from_hours(hours: Dict[str, Dict[str, str]]) -> bool:
    """Determine if a bar should be open now based on its hours dict.

    The current time is evaluated in the timezone specified by the
    ``BAR_TIMEZONE`` environment variable (falling back to ``TZ`` if set).
    If neither variable is defined the server's local timezone is used.
    """
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
    return is_open_now_from_hours(hours)


def load_bars_from_db() -> None:
    """Populate in-memory bars dict from the database."""
    db = SessionLocal()
    try:
        bars.clear()
        for b in db.query(BarModel).all():
            hours = json.loads(b.opening_hours) if b.opening_hours else {}
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
                is_open_now=is_open_now_from_hours(hours) and not (b.manual_closed or False),
                manual_closed=b.manual_closed or False,
                opening_hours=hours,
                promo_label=b.promo_label,
                tags=json.loads(b.tags) if b.tags else [],
            )
            # Load categories for the bar
            for c in b.categories:
                bar.categories[c.id] = Category(
                    id=c.id,
                    name=c.name,
                    description=c.description or "",
                    display_order=c.sort_order,
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
                    photo_url=item.photo,
                )
            # Load user assignments
            bar.bar_admin_ids = []
            bar.bartender_ids = []
            bar.pending_bartender_ids = []
            roles = (
                db.query(UserBarRole)
                .filter(UserBarRole.bar_id == b.id)
                .all()
            )
            for r in roles:
                if r.role == RoleEnum.BARADMIN:
                    bar.bar_admin_ids.append(r.user_id)
                    if r.user_id in users:
                        users[r.user_id].bar_id = b.id
                        users[r.user_id].role = "bar_admin"
                elif r.role == RoleEnum.BARTENDER:
                    bar.bartender_ids.append(r.user_id)
                    if r.user_id in users:
                        users[r.user_id].bar_id = b.id
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
        hours = json.loads(b.opening_hours) if b.opening_hours else {}
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
            is_open_now=is_open_now_from_hours(hours) and not (b.manual_closed or False),
            manual_closed=b.manual_closed or False,
            opening_hours=hours,
            promo_label=b.promo_label,
            tags=json.loads(b.tags) if b.tags else [],
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
        hours = json.loads(b.opening_hours) if b.opening_hours else {}
        bar.opening_hours = hours
        bar.manual_closed = b.manual_closed or False
        bar.is_open_now = is_open_now_from_hours(hours) and not bar.manual_closed
        bar.promo_label = b.promo_label
        bar.tags = json.loads(b.tags) if b.tags else []
        bar.categories.clear()
        bar.products.clear()
    for c in b.categories:
        bar.categories[c.id] = Category(
            id=c.id,
            name=c.name,
            description=c.description or "",
            display_order=c.sort_order,
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
            photo_url=item.photo,
        )
    # Load user assignments
    bar.bar_admin_ids = []
    bar.bartender_ids = []
    bar.pending_bartender_ids = []
    roles = db.query(UserBarRole).filter(UserBarRole.bar_id == bar_id).all()
    for r in roles:
        if r.role == RoleEnum.BARADMIN:
            bar.bar_admin_ids.append(r.user_id)
            if r.user_id in users:
                users[r.user_id].bar_id = bar_id
                users[r.user_id].role = "bar_admin"
        elif r.role == RoleEnum.BARTENDER:
            bar.bartender_ids.append(r.user_id)
            if r.user_id in users:
                users[r.user_id].bar_id = bar_id
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
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
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
            bar.distance_km = _haversine_km(float(lat), float(lng), float(bar.latitude), float(bar.longitude))
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
    # Determine a random selection of open bars within 20km for the "Consigliati" section.
    if lat is not None and lng is not None:
        nearby_pool = [
            b
            for b in db_bars
            if b.is_open_now
            and b.distance_km is not None
            and b.distance_km <= 20
        ]
    else:
        nearby_pool = [b for b in db_bars if b.is_open_now]
    recommended_bars = random.sample(nearby_pool, min(5, len(nearby_pool)))
    if lat is not None and lng is not None:
        rated_within = [
            b
            for b in results
            if b.rating is not None
            and b.distance_km is not None
            and b.distance_km <= 5
        ]
        rated_within.sort(key=lambda b: (-b.rating, b.distance_km))
        top_bars = rated_within[:5]
        top_bars_message = None
        if not top_bars:
            top_bars_message = "Non ci sono bar nelle tue vicinanze."
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
            "photo_url": make_absolute_url(bar.photo_url, request) if request else bar.photo_url,
        }
        for bar in bars.values()
        if term in bar.name.lower() or term in bar.address.lower() or term in bar.city.lower() or term in bar.state.lower()
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
    description: Optional[str] = None
    photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = 0.0
    is_open_now: Optional[bool] = False
    opening_hours: Optional[Dict[str, Dict[str, str]]] = None
    manual_closed: Optional[bool] = False
    promo_label: Optional[str] = None
    tags: Optional[str] = None


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
    promo_label: Optional[str] = None
    tags: Optional[str] = None

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

    class Config:
        orm_mode = True


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
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
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
        line_vat = calculate_vat_from_gross(price, Decimal(menu_item.vat_rate)) * item.qty
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
        status="completed",
        items=order_items,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@app.post("/api/payouts/run", response_model=PayoutRead, status_code=status.HTTP_201_CREATED)
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
        category = bar.categories.get(prod.category_id)
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
    )


@app.get("/bars/{bar_id}/add_to_cart")
async def add_to_cart(request: Request, bar_id: int):
    """Add a product to the cart using query parameters (e.g. ?product_id=1)."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    product_id = int(request.query_params.get("product_id", 0))
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    product = bar.products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    cart = get_cart_for_user(user)
    if cart.bar_id and cart.bar_id != bar_id:
        products_by_category: Dict[Category, List[Product]] = {}
        for prod in bar.products.values():
            category = bar.categories.get(prod.category_id)
            products_by_category.setdefault(category, []).append(prod)
        return render_template(
            "bar_detail.html",
            request=request,
            bar=bar,
            products_by_category=products_by_category,
            error="Please clear your cart before ordering from another bar.",
        )
    if cart.bar_id is None:
        cart.bar_id = bar_id
    cart.add(product)
    return RedirectResponse(url=f"/bars/{bar_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cart = get_cart_for_user(user)
    current_bar: Optional[Bar] = bars.get(cart.bar_id) if cart.bar_id else None
    return render_template(
        "cart.html",
        request=request,
        cart=cart,
        bar=current_bar,
    )


@app.get("/cart/update")
async def update_cart(request: Request):
    """Update item quantity or remove item in the cart using query parameters."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    try:
        product_id = int(request.query_params.get("product_id", 0))
        quantity = int(request.query_params.get("quantity", 0))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid parameters")
    cart = get_cart_for_user(user)
    cart.update_quantity(product_id, quantity)
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
    return RedirectResponse(url="/cart", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/cart/checkout")
async def checkout(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cart = get_cart_for_user(user)
    table_id = request.query_params.get("table_id")
    if table_id is not None:
        try:
            cart.table_id = int(table_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid table")
    if cart.table_id is None:
        raise HTTPException(status_code=400, detail="Please select a table before checking out")
    order_total = cart.total_price()
    if user.credit < order_total:
        raise HTTPException(status_code=400, detail="Insufficient credit")
    user.credit -= order_total
    bar = bars.get(cart.bar_id) if cart.bar_id else None
    if bar:
        user.transactions.append(
            Transaction(bar.id, bar.name, list(cart.items.values()), order_total)
        )
    cart.clear()
    return render_template(
        "order_success.html",
        request=request,
        total=order_total,
        remaining=user.credit,
    )


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
    )


@app.get("/topup", response_class=HTMLResponse)
async def topup(request: Request):
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
            return render_template("topup.html", request=request, error="Invalid amount")
        # In a real application, integrate with a payment gateway here
        user.credit += add_amount
        return render_template("topup.html", request=request, success=True, amount=add_amount)
    return render_template("topup.html", request=request)


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
        if username in users_by_username or db.query(User).filter(User.username == username).first():
            return render_template("register.html", request=request, error="Username already taken")
        if email in users_by_email or db.query(User).filter(User.email == email).first():
            return render_template("register.html", request=request, error="Email already taken")
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
    return render_template("register.html", request=request, error="All fields are required")


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
                    user = DemoUser(
                        id=db_user.id,
                        username=db_user.username,
                        password=password,
                        email=db_user.email,
                        phone=db_user.phone or "",
                        prefix=db_user.prefix or "",
                        role=role_map.get(db_user.role, "customer"),
                    )
                    users[user.id] = user
                    users_by_email[user.email] = user
                    users_by_username[user.username] = user
        if not user or user.password != password:
            return render_template("login.html", request=request, error="Invalid credentials")
        request.session["user_id"] = user.id
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("login.html", request=request, error="Email and password required")


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
        bar = bars.get(user.bar_id)
        return render_template("bar_admin_dashboard.html", request=request, bar=bar)
    if user.is_bartender:
        bar = bars.get(user.bar_id)
        return render_template("bartender_dashboard.html", request=request, bar=bar)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


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
    return render_template("admin_new_bar.html", request=request)


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
    rating = form.get("rating")
    manual_closed = form.get("manual_closed") == "on"
    promo_label = form.get("promo_label")
    tags = form.get("tags")
    tags_json = json.dumps([t.strip() for t in tags.split(",") if t.strip()]) if tags else None
    photo_file = form.get("photo")
    hours = {}
    for i in range(7):
        o = form.get(f"open_{i}")
        c = form.get(f"close_{i}")
        if o and c:
            hours[str(i)] = {"open": o, "close": c}
    opening_hours = json.dumps(hours) if hours else None
    photo_url = None
    if isinstance(photo_file, UploadFile) and photo_file.filename:
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        _, ext = os.path.splitext(photo_file.filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        photo_url = f"/static/uploads/{filename}"
    if not all([name, address, city, state, latitude, longitude, description]):
        return render_template("admin_new_bar.html", request=request, error="All fields are required")
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
        promo_label=promo_label,
        tags=tags_json,
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
        promo_label=promo_label,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
    )
    return RedirectResponse(url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/bars/edit/{bar_id}", response_class=HTMLResponse)
async def edit_bar_options(request: Request, bar_id: int, db: Session = Depends(get_db)):
    """Display links to different bar management pages."""
    user = get_current_user(request)
    bar = db.get(BarModel, bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (user.is_super_admin or (user.is_bar_admin and user.bar_id == bar_id)):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_edit_bar_options.html", request=request, bar=bar)


@app.get("/admin/bars/edit/{bar_id}/info", response_class=HTMLResponse)
async def edit_bar_form(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    bar = db.get(BarModel, bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (user.is_super_admin or (user.is_bar_admin and user.bar_id == bar_id)):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    tags_csv = ", ".join(json.loads(bar.tags)) if bar.tags else ""
    hours = json.loads(bar.opening_hours) if bar.opening_hours else {}
    return render_template(
        "admin_edit_bar.html",
        request=request,
        bar=bar,
        tags_csv=tags_csv,
        hours=hours,
    )


@app.post("/admin/bars/edit/{bar_id}/info")
async def edit_bar_post(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    bar = db.get(BarModel, bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (user.is_super_admin or (user.is_bar_admin and user.bar_id == bar_id)):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    address = form.get("address")
    city = form.get("city")
    state = form.get("state")
    latitude = form.get("latitude")
    longitude = form.get("longitude")
    description = form.get("description")
    rating = form.get("rating")
    manual_closed = form.get("manual_closed") == "on"
    promo_label = form.get("promo_label")
    tags = form.get("tags")
    tags_json = json.dumps([t.strip() for t in tags.split(",") if t.strip()]) if tags else None
    photo_file = form.get("photo")
    photo_url = bar.photo_url
    hours = {}
    for i in range(7):
        o = form.get(f"open_{i}")
        c = form.get(f"close_{i}")
        if o and c:
            hours[str(i)] = {"open": o, "close": c}
    opening_hours = json.dumps(hours) if hours else None
    if isinstance(photo_file, UploadFile) and photo_file.filename:
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
        bar.promo_label = promo_label
        bar.tags = tags_json
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
            mem_bar.promo_label = promo_label
            mem_bar.tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        if user.is_super_admin:
            return RedirectResponse(url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "admin_edit_bar.html", request=request, bar=bar, hours=hours
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
    menu_item_ids = [m.id for m in db.query(MenuItem.id).filter(MenuItem.bar_id == bar_id)]
    if menu_item_ids:
        db.query(MenuVariant).filter(MenuVariant.menu_item_id.in_(menu_item_ids)).delete(synchronize_session=False)
    db.query(MenuItem).filter(MenuItem.bar_id == bar_id).delete(synchronize_session=False)

    db.query(CategoryModel).filter(CategoryModel.bar_id == bar_id).delete(synchronize_session=False)
    db.query(UserBarRole).filter(UserBarRole.bar_id == bar_id).delete(synchronize_session=False)

    order_ids = [o.id for o in db.query(Order.id).filter(Order.bar_id == bar_id)]
    if order_ids:
        db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
    db.query(Order).filter(Order.bar_id == bar_id).delete(synchronize_session=False)

    db.query(Payout).filter(Payout.bar_id == bar_id).delete(synchronize_session=False)

    db.delete(bar)
    db.commit()
    bars.pop(bar_id, None)
    return RedirectResponse(url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/bars/{bar_id}/users", response_class=HTMLResponse)
async def manage_bar_users(request: Request, bar_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar or not user or not (
        user.is_super_admin or (user.is_bar_admin and user.bar_id == bar_id)
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    staff = [
        _load_demo_user(uid, db) for uid in bar.bar_admin_ids + bar.bartender_ids
    ]
    return render_template(
        "admin_bar_users.html", request=request, bar=bar, staff=staff
    )


@app.post("/admin/bars/{bar_id}/users", response_class=HTMLResponse)
async def manage_bar_users_post(
    request: Request, bar_id: int, db: Session = Depends(get_db)
):
    current = get_current_user(request)
    bar = refresh_bar_from_db(bar_id, db)
    if not bar or not current or not (
        current.is_super_admin or (current.is_bar_admin and current.bar_id == bar_id)
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
                demo.bar_id = bar_id
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
        elif username in users_by_username or db.query(User).filter(User.username == username).first():
            error = "Username already taken"
        elif email in users_by_email or db.query(User).filter(User.email == email).first():
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
                bar_id=bar_id,
            )
            users[demo.id] = demo
            users_by_username[demo.username] = demo
            users_by_email[demo.email] = demo
            if role == "bar_admin":
                bar.bar_admin_ids.append(demo.id)
            else:
                bar.bartender_ids.append(demo.id)
            message = "User created"
    staff = [
        _load_demo_user(uid, db) for uid in bar.bar_admin_ids + bar.bartender_ids
    ]
    return render_template(
        "admin_bar_users.html",
        request=request,
        bar=bar,
        staff=staff,
        error=error,
        message=message,
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
    user.bar_id = bar_id
    user.pending_bar_id = None
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
    cancellation_rate = (
        cancelled_orders / total_orders * 100 if total_orders else 0
    )

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
            extract('hour', Order.created_at).label("hour"),
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
            extract('hour', Order.created_at).label("hour"),
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
        if existing:
            existing.username = db_user.username
            existing.email = db_user.email
            existing.phone = db_user.phone or ""
            existing.prefix = db_user.prefix or ""
            existing.role = role_map.get(db_user.role, "customer")
        else:
            demo = DemoUser(
                id=db_user.id,
                username=db_user.username,
                password="",
                email=db_user.email,
                phone=db_user.phone or "",
                prefix=db_user.prefix or "",
                role=role_map.get(db_user.role, "customer"),
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
    user = DemoUser(
        id=db_user.id,
        username=db_user.username,
        password="",
        email=db_user.email,
        phone=db_user.phone or "",
        prefix=db_user.prefix or "",
        role=role_map.get(db_user.role, "customer"),
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
        or (current.is_bar_admin and user.bar_id == current.bar_id)
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        "admin_edit_user.html", request=request, user=user, bars=bars.values(), current=current
    )


@app.post("/admin/users/edit/{user_id}", response_class=HTMLResponse)
async def update_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    current = get_current_user(request)
    if not current:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    user = _load_demo_user(user_id, db)
    if not (
        current.is_super_admin
        or (current.is_bar_admin and user.bar_id == current.bar_id)
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    email = form.get("email")
    prefix = form.get("prefix")
    phone = form.get("phone")
    role = form.get("role")
    bar_id = form.get("bar_id")
    credit = form.get("credit")
    if not (username and email is not None and role is not None):
        return render_template(
            "admin_edit_user.html", request=request, user=user, bars=bars.values(), current=current
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
        email in users_by_email
        or db.query(User).filter(User.email == email).first()
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
        bar_id = str(current.bar_id)
        credit = str(user.credit)
    user.role = role
    user.bar_id = int(bar_id) if bar_id else None
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
    db_user.role = role_enum_map.get(role, RoleEnum.CUSTOMER)
    db.commit()
    # Update user-bar role association
    existing_role = (
        db.query(UserBarRole)
        .filter(UserBarRole.user_id == user_id, UserBarRole.bar_id == user.bar_id)
        .first()
    )
    if user.bar_id:
        if existing_role:
            existing_role.role = role_enum_map.get(role, RoleEnum.CUSTOMER)
        else:
            db.add(
                UserBarRole(
                    user_id=user_id, bar_id=user.bar_id, role=role_enum_map.get(role, RoleEnum.CUSTOMER)
                )
            )
    elif existing_role:
        db.delete(existing_role)
    db.commit()
    # Update in-memory bar assignments
    for b in bars.values():
        if user_id in b.bar_admin_ids:
            b.bar_admin_ids.remove(user_id)
        if user_id in b.bartender_ids:
            b.bartender_ids.remove(user_id)
    if user.bar_id:
        target = bars.get(user.bar_id) or refresh_bar_from_db(user.bar_id, db)
        if role == "bar_admin":
            target.bar_admin_ids.append(user_id)
        elif role == "bartender":
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    description = form.get("description")
    display_order = form.get("display_order") or 0
    photo_file = form.get("photo")
    photo_url = None
    if isinstance(photo_file, UploadFile) and photo_file.filename:
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        _, ext = os.path.splitext(photo_file.filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        photo_url = f"/static/uploads/{filename}"
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
        photo_url=photo_url,
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
        photo_url=photo_url,
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
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


@app.get(
    "/bar/{bar_id}/categories/{category_id}/products", response_class=HTMLResponse
)
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    products = sorted(
        [p for p in bar.products.values() if p.category_id == category_id],
        key=lambda p: p.display_order,
    )
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    price = form.get("price")
    description = form.get("description")
    display_order = form.get("display_order") or 0
    photo_file = form.get("photo")
    photo_url = None
    if isinstance(photo_file, UploadFile) and photo_file.filename:
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        _, ext = os.path.splitext(photo_file.filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        photo_url = f"/static/uploads/{filename}"
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
    product = Product(
        id=db_item.id,
        category_id=category_id,
        name=name,
        price=price_val,
        description=description,
        display_order=order_val,
        photo_url=photo_url,
    )
    bar.products[product.id] = product
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories/{category_id}/products",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post(
    "/bar/{bar_id}/categories/{category_id}/products/{product_id}/delete"
)
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
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
    product = bar.products.get(product_id)
    if not category or not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not user or not (
        user.is_super_admin
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
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
    product = bar.products.get(product_id)
    if not category or not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not user or not (
        user.is_super_admin
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    price = form.get("price")
    description = form.get("description")
    display_order = form.get("display_order") or product.display_order
    photo_file = form.get("photo")
    db_item = db.get(MenuItem, product_id)
    if name:
        product.name = name
        if db_item:
            db_item.name = name
    if description:
        product.description = description
        if db_item:
            db_item.description = description
    if price:
        try:
            price_val = float(price)
            price_dec = Decimal(price)
            product.price = price_val
            if db_item:
                db_item.price_chf = price_dec
        except ValueError:
            pass
    try:
        order_val = int(display_order)
        product.display_order = order_val
        if db_item:
            db_item.sort_order = order_val
    except ValueError:
        pass
    if isinstance(photo_file, UploadFile) and photo_file.filename:
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        _, ext = os.path.splitext(photo_file.filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        product.photo_url = f"/static/uploads/{filename}"
        if db_item:
            db_item.photo = product.photo_url
    if db_item:
        db.add(db_item)
        db.commit()
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories/{category_id}/products",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get(
    "/bar/{bar_id}/categories/{category_id}/edit", response_class=HTMLResponse
)
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
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
        or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))
    ):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    form = await request.form()
    name = form.get("name")
    description = form.get("description")
    display_order = form.get("display_order") or category.display_order
    photo_file = form.get("photo")
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
    if isinstance(photo_file, UploadFile) and photo_file.filename:
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        _, ext = os.path.splitext(photo_file.filename)
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await photo_file.read())
        category.photo_url = f"/static/uploads/{filename}"
        if db_category:
            db_category.photo_url = category.photo_url
    if db_category:
        db.commit()
    return RedirectResponse(
        url=f"/bar/{bar_id}/categories", status_code=status.HTTP_303_SEE_OTHER
    )
