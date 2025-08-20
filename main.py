"""
Simplified prototype of the SiplyGo platform using FastAPI and Jinja2 templates.

This application is not production‑ready but demonstrates the core building blocks
required to implement a premium bar ordering platform.  It includes:

* A home page that lists bars near the user (using a static data set for now).
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

from typing import Dict, List, Optional

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables from a .env file if present
load_dotenv()

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
    ):
        self.id = id
        self.name = name
        self.address = address
        self.city = city
        self.state = state
        self.latitude = latitude
        self.longitude = longitude
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


class Cart:
    def __init__(self):
        self.items: Dict[int, CartItem] = {}
        self.table_id: Optional[int] = None

    def add(self, product: Product):
        if product.id in self.items:
            self.items[product.id].quantity += 1
        else:
            self.items[product.id] = CartItem(product, 1)

    def remove(self, product_id: int):
        if product_id in self.items:
            del self.items[product_id]

    def update_quantity(self, product_id: int, quantity: int):
        if product_id in self.items:
            if quantity <= 0:
                del self.items[product_id]
            else:
                self.items[product_id].quantity = quantity

    def total_price(self) -> float:
        return sum(item.total for item in self.items.values())

    def clear(self):
        self.items.clear()
        self.table_id = None


# -----------------------------------------------------------------------------
# Application initialisation
# -----------------------------------------------------------------------------

app = FastAPI()

# Mount a static files directory for CSS/JS/image assets if needed
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable server-side sessions for authentication
app.add_middleware(SessionMiddleware, secret_key="dev-secret")

# Jinja2 environment for rendering HTML templates
templates_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
templates_env.globals["GOOGLE_MAPS_API_KEY"] = os.getenv("GOOGLE_MAPS_API_KEY", "")

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


def seed_data():
    """Populate the store with a demo bar, categories, products and tables."""
    global next_bar_id, next_category_id, next_product_id, next_table_id

    bar = Bar(
        id=next_bar_id,
        name="Bar Sport",
        address="Via Principale 1",
        city="Airolo",
        state="Ticino",
        latitude=46.5269,
        longitude=8.6086,
    )
    next_bar_id += 1

    # Categories
    cat_coffee = Category(id=next_category_id, name="Coffee", description="Espresso, cappuccino and more")
    next_category_id += 1
    cat_cocktails = Category(id=next_category_id, name="Cocktails", description="Classic and signature cocktails")
    next_category_id += 1
    bar.categories[cat_coffee.id] = cat_coffee
    bar.categories[cat_cocktails.id] = cat_cocktails

    # Products
    prod_espresso = Product(id=next_product_id, category_id=cat_coffee.id, name="Espresso", price=2.5,
                            description="Rich Italian espresso")
    next_product_id += 1
    prod_cappuccino = Product(id=next_product_id, category_id=cat_coffee.id, name="Cappuccino", price=3.0,
                              description="Creamy cappuccino with milk foam")
    next_product_id += 1
    prod_mojito = Product(id=next_product_id, category_id=cat_cocktails.id, name="Mojito", price=8.0,
                          description="Rum, mint, lime and soda")
    next_product_id += 1
    bar.products[prod_espresso.id] = prod_espresso
    bar.products[prod_cappuccino.id] = prod_cappuccino
    bar.products[prod_mojito.id] = prod_mojito

    # Tables
    for table_number in range(1, 6):
        table = Table(id=next_table_id, name=f"Table {table_number}")
        next_table_id += 1
        bar.tables[table.id] = table

    bars[bar.id] = bar


seed_data()


def seed_super_admin():
    """Create the default super admin account."""
    global next_user_id
    admin = User(
        id=next_user_id,
        username="andreastojov",
        password="Andrea24",
        email="andreastojov@gmail.com",
        phone="5551234",
        prefix="+41",
        role="super_admin",
    )
    users[admin.id] = admin
    users_by_username[admin.username] = admin
    users_by_email[admin.email] = admin
    next_user_id += 1


def seed_bar_staff():
    """Create demo bar admin and bartender for the first bar."""
    global next_user_id
    if not bars:
        return
    bar_id = next(iter(bars))
    bar = bars[bar_id]
    # Bar admin
    admin_user = User(
        id=next_user_id,
        username="baradmin",
        password="baradmin",
        email="baradmin@example.com",
        phone="5555678",
        prefix="+41",
        role="bar_admin",
        bar_id=bar_id,
    )
    users[admin_user.id] = admin_user
    users_by_username[admin_user.username] = admin_user
    users_by_email[admin_user.email] = admin_user
    bar.bar_admin_ids.append(admin_user.id)
    next_user_id += 1
    # Bartender
    bartender_user = User(
        id=next_user_id,
        username="bartender",
        password="bartender",
        email="bartender@example.com",
        phone="5559012",
        prefix="+41",
        role="bartender",
        bar_id=bar_id,
    )
    users[bartender_user.id] = bartender_user
    users_by_username[bartender_user.username] = bartender_user
    users_by_email[bartender_user.email] = bartender_user
    bar.bartender_ids.append(bartender_user.id)
    next_user_id += 1


seed_super_admin()
seed_bar_staff()


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
    cart.add(product)
    return RedirectResponse(url=f"/bars/{bar_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cart = get_cart_for_user(user)
    # For demonstration, select the first bar from data set; in a real app the cart
    # would be associated with a specific bar when items are added.
    current_bar: Optional[Bar] = next(iter(bars.values())) if bars else None
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
    if cart.table_id is None:
        raise HTTPException(status_code=400, detail="Please select a table before checking out")
    order_total = cart.total_price()
    cart.clear()
    return render_template("order_success.html", request=request, total=order_total)


# -----------------------------------------------------------------------------
# Authentication routes
# -----------------------------------------------------------------------------


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    username = request.query_params.get("username")
    password = request.query_params.get("password")
    email = request.query_params.get("email")
    phone = request.query_params.get("phone")
    prefix = request.query_params.get("prefix")
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
    return render_template("register.html", request=request)


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    email = request.query_params.get("email")
    password = request.query_params.get("password")
    if email and password:
        user = users_by_email.get(email)
        if not user or user.password != password:
            return render_template("login.html", request=request, error="Invalid credentials")
        request.session["user_id"] = user.id
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("login.html", request=request)


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
    if not all([name, address, city, state, latitude, longitude]):
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
    if all([name, address, city, state, latitude, longitude]):
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
    if username and password and role is not None:
        if username != user.username and username in users_by_username:
            return render_template("admin_edit_user.html", request=request, user=user, bars=bars.values(), error="Username already taken")
        # Update username mapping
        if username != user.username:
            del users_by_username[user.username]
            user.username = username
            users_by_username[user.username] = user
        user.password = password
        user.role = role
        user.bar_id = int(bar_id) if bar_id else None
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
