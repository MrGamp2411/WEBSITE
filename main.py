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
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database import Base, SessionLocal, engine, get_db
from models import Bar as BarModel, MenuItem, Order, OrderItem, Payout, User, RoleEnum
from pydantic import BaseModel
from decimal import Decimal
from finance import (
    calculate_platform_fee,
    calculate_payout,
    calculate_vat_from_gross,
)
from payouts import schedule_payout
from audit import log_action

# -----------------------------------------------------------------------------
# Data models (in-memory for demonstration purposes)
# -----------------------------------------------------------------------------

class Category:
    def __init__(self, id: int, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description


class Product:
    def __init__(self, id: int, category_id: int, name: str, price: float, description: str):
        self.id = id
        self.category_id = category_id
        self.name = name
        self.price = price
        self.description = description


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
    ):
        self.id = id
        self.name = name
        self.address = address
        self.city = city
        self.state = state
        self.latitude = latitude
        self.longitude = longitude
        self.description = description
        self.categories: Dict[int, Category] = {}
        self.products: Dict[int, Product] = {}
        self.tables: Dict[int, Table] = {}
        # Users assigned to this bar
        self.bar_admin_ids: List[int] = []
        self.bartender_ids: List[int] = []
        # Bartenders that still need to confirm the assignment
        self.pending_bartender_ids: List[int] = []


class User:
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

@app.on_event("startup")
def on_startup():
    """Initialise database tables on startup."""
    Base.metadata.create_all(bind=engine)
    seed_super_admin()


@app.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    """Simple health check returning DB status."""
    try:
        db.execute("SELECT 1")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=500, detail="DB unavailable")

# Jinja2 environment for rendering HTML templates
templates_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# -----------------------------------------------------------------------------
# In-memory store with sample data
# -----------------------------------------------------------------------------

bars: Dict[int, Bar] = {}
next_bar_id = 1
next_category_id = 1
next_product_id = 1
next_table_id = 1

# User storage
users: Dict[int, User] = {}
users_by_username: Dict[str, User] = {}
users_by_email: Dict[str, User] = {}
next_user_id = 1

# Cart storage per user
user_carts: Dict[int, Cart] = {}



# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def get_current_user(request: Request) -> Optional[User]:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return users.get(user_id)


def get_cart_for_user(user: User) -> Cart:
    return user_carts.setdefault(user.id, Cart())


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
        last_bar_id = request.session.get("last_bar_id")
        if last_bar_id is not None:
            context.setdefault("last_bar", bars.get(last_bar_id))

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
async def home(request: Request):
    """Home page listing available bars."""
    return render_template("home.html", request=request, bars=bars.values())


@app.get("/search", response_class=HTMLResponse)
async def search_bars(request: Request, q: str = ""):
    term = q.lower()
    results = [
        bar for bar in bars.values()
        if term in bar.name.lower() or term in bar.address.lower() or term in bar.city.lower() or term in bar.state.lower()
    ]
    return render_template("search.html", request=request, bars=results, query=q)


@app.get("/api/search")
async def api_search(q: str = ""):
    term = q.lower()
    results = [
        {
            "id": bar.id,
            "name": bar.name,
            "address": bar.address,
            "city": bar.city,
            "state": bar.state,
            "description": bar.description,
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


class BarRead(BaseModel):
    id: int
    name: str
    slug: str
    address: Optional[str] = None

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
    return db.query(BarModel).all()


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
    request.session["last_bar_id"] = bar.id
    # group products by category
    products_by_category: Dict[Category, List[Product]] = {}
    for prod in bar.products.values():
        category = bar.categories.get(prod.category_id)
        if category not in products_by_category:
            products_by_category[category] = []
        products_by_category[category].append(prod)
    return render_template(
        "bar_detail.html",
        request=request,
        bar=bar,
        products_by_category=products_by_category,
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
async def register(request: Request):
    """Handle user registration submissions."""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    email = form.get("email")
    phone = form.get("phone")
    prefix = form.get("prefix")
    if all([username, password, email, phone, prefix]):
        if username in users_by_username:
            return render_template("register.html", request=request, error="Username already taken")
        if email in users_by_email:
            return render_template("register.html", request=request, error="Email already taken")
        global next_user_id
        user = User(
            id=next_user_id,
            username=username,
            password=password,
            email=email,
            phone=phone,
            prefix=prefix,
        )
        next_user_id += 1
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
async def login(request: Request):
    """Handle login submissions."""
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    if email and password:
        user = users_by_email.get(email)
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
async def admin_bars_view(request: Request):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_bars.html", request=request, bars=bars.values())


@app.get("/admin/bars/new", response_class=HTMLResponse)
async def new_bar(request: Request):
    """Display the creation form and handle adding a new bar."""
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    name = request.query_params.get("name")
    address = request.query_params.get("address")
    city = request.query_params.get("city")
    state = request.query_params.get("state")
    latitude = request.query_params.get("latitude")
    longitude = request.query_params.get("longitude")
    description = request.query_params.get("description")
    if not all([name, address, city, state, latitude, longitude, description]):
        # Show empty form when required parameters are missing
        return render_template("admin_new_bar.html", request=request)
    try:
        lat = float(latitude)
        lon = float(longitude)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    global next_bar_id
    bar = Bar(
        id=next_bar_id,
        name=name,
        address=address,
        city=city,
        state=state,
        latitude=lat,
        longitude=lon,
        description=description,
    )
    next_bar_id += 1
    bars[bar.id] = bar
    return RedirectResponse(url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/bars/edit/{bar_id}", response_class=HTMLResponse)
async def edit_bar(request: Request, bar_id: int):
    user = get_current_user(request)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (user.is_super_admin or (user.is_bar_admin and user.bar_id == bar_id)):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    name = request.query_params.get("name")
    address = request.query_params.get("address")
    city = request.query_params.get("city")
    state = request.query_params.get("state")
    latitude = request.query_params.get("latitude")
    longitude = request.query_params.get("longitude")
    description = request.query_params.get("description")
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
        if user.is_super_admin:
            return RedirectResponse(url="/admin/bars", status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_edit_bar.html", request=request, bar=bar)


@app.get("/admin/bars/{bar_id}/add_user", response_class=HTMLResponse)
async def add_user_to_bar(request: Request, bar_id: int):
    user = get_current_user(request)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (user.is_super_admin or (user.is_bar_admin and user.bar_id == bar_id)):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    global next_user_id
    username = request.query_params.get("username")
    password = request.query_params.get("password")
    email = request.query_params.get("email")
    role = request.query_params.get("role")
    if username and role:
        if role not in ("bar_admin", "bartender"):
            raise HTTPException(status_code=400, detail="Invalid role")
        existing = users_by_username.get(username)
        if role == "bar_admin":
            if existing:
                return render_template(
                    "admin_add_user_to_bar.html",
                    request=request,
                    bar=bar,
                    error="Username already taken",
                )
            if not password or not email:
                return render_template(
                    "admin_add_user_to_bar.html",
                    request=request,
                    bar=bar,
                    error="Email and password required",
                )
            if email in users_by_email:
                return render_template(
                    "admin_add_user_to_bar.html",
                    request=request,
                    bar=bar,
                    error="Email already taken",
                )
            new_user = User(
                id=next_user_id,
                username=username,
                password=password,
                email=email,
                role="bar_admin",
                bar_id=bar_id,
            )
            next_user_id += 1
            users[new_user.id] = new_user
            users_by_username[new_user.username] = new_user
            users_by_email[new_user.email] = new_user
            bar.bar_admin_ids.append(new_user.id)
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:  # bartender
            if existing:
                existing.pending_bar_id = bar_id
                bar.pending_bartender_ids.append(existing.id)
                return render_template(
                    "admin_add_user_to_bar.html",
                    request=request,
                    bar=bar,
                    message="Invitation sent",
                )
            if not password or not email:
                return render_template(
                    "admin_add_user_to_bar.html",
                    request=request,
                    bar=bar,
                    error="Email and password required",
                )
            if email in users_by_email:
                return render_template(
                    "admin_add_user_to_bar.html",
                    request=request,
                    bar=bar,
                    error="Email already taken",
                )
            new_user = User(
                id=next_user_id,
                username=username,
                password=password,
                email=email,
                role="bartender_pending",
                pending_bar_id=bar_id,
            )
            next_user_id += 1
            users[new_user.id] = new_user
            users_by_username[new_user.username] = new_user
            users_by_email[new_user.email] = new_user
            bar.pending_bartender_ids.append(new_user.id)
            return render_template(
                "admin_add_user_to_bar.html",
                request=request,
                bar=bar,
                message="Invitation sent",
            )
    return render_template("admin_add_user_to_bar.html", request=request, bar=bar)


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


@app.get("/admin/profile", response_class=HTMLResponse)
async def admin_profile(request: Request):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_profile.html", request=request)


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_view(request: Request):
    user = get_current_user(request)
    if not user or not user.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_users.html", request=request, users=users.values(), bars=bars)


@app.get("/admin/users/edit/{user_id}", response_class=HTMLResponse)
async def edit_user(request: Request, user_id: int):
    current = get_current_user(request)
    if not current or not current.is_super_admin:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    username = request.query_params.get("username")
    password = request.query_params.get("password")
    role = request.query_params.get("role")
    bar_id = request.query_params.get("bar_id")
    credit = request.query_params.get("credit")
    if username and password and role is not None and credit is not None:
        if username != user.username and username in users_by_username:
            return render_template(
                "admin_edit_user.html",
                request=request,
                user=user,
                bars=bars.values(),
                error="Username already taken",
            )
        # Update username mapping
        if username != user.username:
            del users_by_username[user.username]
            user.username = username
            users_by_username[user.username] = user
        user.password = password
        user.role = role
        user.bar_id = int(bar_id) if bar_id else None
        try:
            user.credit = float(credit)
        except ValueError:
            return render_template(
                "admin_edit_user.html",
                request=request,
                user=user,
                bars=bars.values(),
                error="Invalid credit amount",
            )
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("admin_edit_user.html", request=request, user=user, bars=bars.values())


@app.get("/bar/{bar_id}/categories/new", response_class=HTMLResponse)
async def bar_new_category(request: Request, bar_id: int):
    user = get_current_user(request)
    bar = bars.get(bar_id)
    if not bar:
        raise HTTPException(status_code=404, detail="Bar not found")
    if not user or not (user.is_super_admin or (user.bar_id == bar_id and (user.is_bar_admin or user.is_bartender))):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    name = request.query_params.get("name")
    description = request.query_params.get("description")
    if name and description:
        global next_category_id
        category = Category(id=next_category_id, name=name, description=description)
        next_category_id += 1
        bar.categories[category.id] = category
        return RedirectResponse(url=f"/bars/{bar_id}", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("bar_new_category.html", request=request, bar=bar)
