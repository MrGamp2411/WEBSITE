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

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.middleware.sessions import SessionMiddleware

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
    def __init__(self, id: int, name: str, address: str, latitude: float, longitude: float):
        self.id = id
        self.name = name
        self.address = address
        self.latitude = latitude
        self.longitude = longitude
        self.categories: Dict[int, Category] = {}
        self.products: Dict[int, Product] = {}
        self.tables: Dict[int, Table] = {}


class User:
    def __init__(self, id: int, username: str, password: str):
        self.id = id
        self.username = username
        self.password = password


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
next_user_id = 1

# Cart storage per user
user_carts: Dict[int, Cart] = {}


def seed_data():
    """Populate the store with a demo bar, categories, products and tables."""
    global next_bar_id, next_category_id, next_product_id, next_table_id

    bar = Bar(id=next_bar_id, name="Bar Sport", address="Via Principale 1, 6780 Airolo",
              latitude=46.5269, longitude=8.6086)
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
        context.setdefault("user", get_current_user(request))
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
    if username and password:
        if username in users_by_username:
            return render_template("register.html", request=request, error="Username already taken")
        global next_user_id
        user = User(id=next_user_id, username=username, password=password)
        next_user_id += 1
        users[user.id] = user
        users_by_username[user.username] = user
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("register.html", request=request)


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    username = request.query_params.get("username")
    password = request.query_params.get("password")
    if username and password:
        user = users_by_username.get(username)
        if not user or user.password != password:
            return render_template("login.html", request=request, error="Invalid credentials")
        request.session["user_id"] = user.id
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template("login.html", request=request)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# Admin endpoints to add a new bar (simplified)

@app.get("/admin/bars/new", response_class=HTMLResponse)
async def new_bar_form(request: Request):
    return render_template("admin_new_bar.html", request=request)


@app.get("/admin/bars/new")
async def create_new_bar(request: Request):
    """Endpoint to create a new bar using query parameters."""
    # Only handle create when query parameters present
    name = request.query_params.get("name")
    address = request.query_params.get("address")
    latitude = request.query_params.get("latitude")
    longitude = request.query_params.get("longitude")
    if not all([name, address, latitude, longitude]):
        # If not all fields provided, show form (GET request) -- handled by new_bar_form
        return await new_bar_form(request)
    try:
        lat = float(latitude)
        lon = float(longitude)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    global next_bar_id
    bar = Bar(id=next_bar_id, name=name, address=address,
              latitude=lat, longitude=lon)
    next_bar_id += 1
    bars[bar.id] = bar
    # Redirect to home
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
