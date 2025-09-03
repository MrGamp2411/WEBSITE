from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Float,
    LargeBinary,
)
from sqlalchemy.orm import relationship

from database import Base


class RoleEnum(str, PyEnum):
    SUPERADMIN = "SuperAdmin"
    BARADMIN = "BarAdmin"
    BARTENDER = "Bartender"
    CUSTOMER = "Customer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.CUSTOMER, nullable=False)
    phone = Column(String(30))
    prefix = Column(String(10))
    twofa_secret = Column(String(32))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    credit = Column(Numeric(10, 2), default=0)

    bar_roles = relationship("UserBarRole", back_populates="user")


class UserCart(Base):
    __tablename__ = "user_carts"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    bar_id = Column(Integer, nullable=True)
    table_id = Column(Integer, nullable=True)
    items_json = Column(Text)

    user = relationship("User")


class Bar(Base):
    __tablename__ = "bars"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    photo_url = Column(String(255))
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    description = Column(Text)
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    opening_hours = Column(Text)
    active = Column(Boolean, default=True)
    zone = Column(String(50))
    rating = Column(Float, default=0.0)
    is_open_now = Column(Boolean, default=False)
    manual_closed = Column(Boolean, default=False)
    promo_label = Column(String(100))
    tags = Column(Text)
    bar_categories = Column(Text)

    categories = relationship("Category", back_populates="bar")
    menu_items = relationship("MenuItem", back_populates="bar")
    tables = relationship("Table", back_populates="bar")


class UserBarRole(Base):
    __tablename__ = "user_bar_roles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bar_id = Column(Integer, ForeignKey("bars.id"), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)

    user = relationship("User", back_populates="bar_roles")
    bar = relationship("Bar")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    photo_url = Column(String(255))
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)

    bar = relationship("Bar", back_populates="categories")
    items = relationship("MenuItem", back_populates="category")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(190))
    price_chf = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(4, 2), default=0)
    sku = Column(String(50))
    photo = Column(String(255))
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    stock_status = Column(String(20), default="in_stock")

    bar = relationship("Bar", back_populates="menu_items")
    category = relationship("Category", back_populates="items")
    variants = relationship("MenuVariant", back_populates="item")


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    bar = relationship("Bar", back_populates="tables")


class MenuVariant(Base):
    __tablename__ = "menu_variants"

    id = Column(Integer, primary_key=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    name = Column(String(100), nullable=False)
    delta_price_chf = Column(Numeric(10, 2), default=0)
    sku = Column(String(50))
    active = Column(Boolean, default=True)

    item = relationship("MenuItem", back_populates="variants")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(
        Integer, ForeignKey("menu_items.id"), unique=True, nullable=False
    )
    mime = Column(String, nullable=False)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class BarClosing(Base):
    __tablename__ = "bar_closings"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id"), nullable=False)
    closed_at = Column(DateTime, default=datetime.utcnow)
    total_revenue = Column(Numeric(10, 2), default=0)

    bar = relationship("Bar")
    orders = relationship("Order", back_populates="closing")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"))
    table_id = Column(Integer, ForeignKey("tables.id"))
    subtotal = Column(Numeric(10, 2), default=0)
    vat_total = Column(Numeric(10, 2), default=0)
    fee_platform_5pct = Column(Numeric(10, 2), default=0)
    payout_due_to_bar = Column(Numeric(10, 2), default=0)
    status = Column(String(30), default="PLACED")
    payment_method = Column(String(30))
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime)
    ready_at = Column(DateTime)
    paid_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    refund_amount = Column(Numeric(10, 2), default=0)
    notes = Column(Text)
    source_channel = Column(String(30))
    closing_id = Column(Integer, ForeignKey("bar_closings.id"))

    items = relationship("OrderItem", back_populates="order")
    customer = relationship("User")
    table = relationship("Table")
    bar = relationship("Bar")
    closing = relationship("BarClosing", back_populates="orders")

    @property
    def customer_name(self):
        return self.customer.username if self.customer else None

    @property
    def customer_prefix(self):
        return self.customer.prefix if self.customer else None

    @property
    def customer_phone(self):
        return self.customer.phone if self.customer else None

    @property
    def table_name(self):
        return self.table.name if self.table else None

    @property
    def bar_name(self):
        return self.bar.name if self.bar else None

    @property
    def total(self):
        return float(self.subtotal + self.vat_total)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    variant_id = Column(Integer, ForeignKey("menu_variants.id"))
    qty = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_vat = Column(Numeric(10, 2), default=0)
    line_total = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")
    variant = relationship("MenuVariant")

    @property
    def menu_item_name(self):
        return self.menu_item.name if self.menu_item else None


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id"), nullable=False)
    amount_chf = Column(Numeric(10, 2), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String(20), default="scheduled")
    paid_at = Column(DateTime)
    reference = Column(String(100))

    bar = relationship("Bar")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True)
    placement = Column(String(50), nullable=False)
    file_url = Column(String(255), nullable=False)
    title = Column(String(100))
    alt = Column(String(100))
    start_at = Column(DateTime)
    end_at = Column(DateTime)
    target_scope = Column(String(20), default="all")
    target_id = Column(Integer)
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    banner_url = Column(String(255))
    start_at = Column(DateTime)
    end_at = Column(DateTime)
    target_scope = Column(String(20), default="all")
    target_id = Column(Integer)
    active = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer)
    payload_json = Column(Text)
    ip = Column(String(50))
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
