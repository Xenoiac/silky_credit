from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    cr_number = Column(String(50), nullable=True)
    vat_number = Column(String(50), nullable=True)
    country = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)  # used as segment
    founded_date = Column(Date, nullable=True)
    branches_count = Column(Integer, default=1)
    acquisition_channel = Column(String(50), default="silky_direct")
    referral_partner_id = Column(String(64), nullable=True)

    settings = relationship("CustomerSetting", back_populates="customer", uselist=False)
    users = relationship("User", back_populates="customer")
    usage_events = relationship("UsageEvent", back_populates="customer")
    pos_transactions = relationship("PosTransaction", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    credit_profiles = relationship("SilkyCreditProfileSnapshot", back_populates="customer")


class CustomerSetting(Base):
    __tablename__ = "customer_settings"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    subscription_plan = Column(String(50), default="standard")
    modules_enabled = Column(Text, default="POS,Inventory")
    go_live_date = Column(Date, nullable=True)
    status = Column(String(50), default="active")

    customer = relationship("Customer", back_populates="settings")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="users")
    usage_events = relationship("UsageEvent", back_populates="user")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    module = Column(String(100), nullable=False)  # POS, Inventory, WMS, ERP, etc.
    event_type = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    customer = relationship("Customer", back_populates="usage_events")
    user = relationship("User", back_populates="usage_events")


class PosTransaction(Base):
    __tablename__ = "pos_transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    date = Column(Date, default=date.today, index=True)
    net_sales = Column(Float, nullable=False)
    branch_id = Column(Integer, nullable=True)
    payment_method = Column(String(50), nullable=True)

    customer = relationship("Customer", back_populates="pos_transactions")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)  # open, paid, overdue
    paid_date = Column(Date, nullable=True)

    customer = relationship("Customer", back_populates="invoices")


class SilkyCreditProfileSnapshot(Base):
    __tablename__ = "silky_credit_profile_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    snapshot_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    viewer_type = Column(String(32), nullable=False)
    usage_mode = Column(String(32), nullable=True)
    subscription_tier = Column(String(32), nullable=True)
    lender_id = Column(String(64), nullable=True)

    dashboard_json = Column(Text, nullable=False)

    credit_score = Column(Integer, nullable=False)
    credit_band = Column(String(4), nullable=False)
    recommended_credit_limit_amount = Column(Float, nullable=False)
    recommended_credit_limit_currency = Column(String(8), default="SAR", nullable=False)
    max_safe_tenor_months = Column(Integer, nullable=False)
    data_quality_comment = Column(Text, nullable=True)

    model_version = Column(String(50), nullable=True)
    model_provider = Column(String(50), nullable=True)
    input_data_date_range = Column(String(100), nullable=True)

    customer = relationship("Customer", back_populates="credit_profiles")
