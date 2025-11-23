from datetime import date, datetime, timedelta
from random import randint, uniform
from typing import Iterable, List

from .db import Base, SessionLocal, engine
from .models import (
    Customer,
    CustomerSetting,
    Invoice,
    PosTransaction,
    UsageEvent,
    User,
)


def _create_users(db, customer: Customer, roles: Iterable[str]) -> List[User]:
    users = [User(customer_id=customer.id, name=role.title(), role=role) for role in roles]
    db.add_all(users)
    db.flush()
    return users


def _seed_usage_events(db, customer: Customer, user_ids: List[int], activity_bias: int) -> None:
    now = datetime.utcnow()
    for day_offset in range(0, 75):
        day = now - timedelta(days=day_offset)
        if randint(0, 100) < activity_bias:
            for _ in range(randint(3, 12)):
                db.add(
                    UsageEvent(
                        customer_id=customer.id,
                        user_id=user_ids[randint(0, len(user_ids) - 1)],
                        module="POS",
                        event_type="login",
                        timestamp=day - timedelta(minutes=randint(0, 600)),
                    )
                )
            for _ in range(randint(0, 4)):
                db.add(
                    UsageEvent(
                        customer_id=customer.id,
                        user_id=user_ids[randint(0, len(user_ids) - 1)],
                        module="Inventory",
                        event_type="stock_update",
                        timestamp=day - timedelta(minutes=randint(0, 600)),
                    )
                )


def _seed_transactions(db, customer: Customer, base: float, volatility: float) -> None:
    today = date.today()
    for month_offset in range(0, 12):
        month_start = today - timedelta(days=month_offset * 30)
        for _ in range(15):
            sales = round(uniform(base * (1 - volatility), base * (1 + volatility)), 2)
            db.add(
                PosTransaction(
                    customer_id=customer.id,
                    date=month_start - timedelta(days=randint(0, 25)),
                    net_sales=sales,
                    branch_id=randint(1, max(customer.branches_count, 1)),
                    payment_method="card",
                )
            )


def _seed_invoices(db, customer: Customer) -> None:
    today = date.today()
    for month_offset in range(0, 6):
        month_start = today - timedelta(days=month_offset * 30)
        for _ in range(4):
            issue = month_start - timedelta(days=randint(0, 10))
            due = issue + timedelta(days=30)
            amount = round(uniform(3500, 24000), 2)
            if randint(0, 100) < 70:
                status = "paid"
                paid_date = due + timedelta(days=randint(-5, 10))
            else:
                status = "overdue"
                paid_date = None

            db.add(
                Invoice(
                    customer_id=customer.id,
                    issue_date=issue,
                    due_date=due,
                    amount=amount,
                    status=status,
                    paid_date=paid_date,
                )
            )


def seed_database() -> None:
    """Create tables and seed a multi-customer demo dataset if DB is empty."""

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Customer).first():
            return

        sample_customers = [
            {
                "legal_name": "Riyadh Burger House Co.",
                "trade_name": "Burger House - Riyadh",
                "city": "Riyadh",
                "industry": "F&B_QSR",
                "subscription_plan": "pro",
                "modules": "POS,Inventory,Invoices",
                "base_sales": 14000,
                "volatility": 0.25,
                "activity_bias": 70,
            },
            {
                "legal_name": "Jeddah Fresh Mart LLC",
                "trade_name": "Fresh Mart",
                "city": "Jeddah",
                "industry": "FMCG",
                "subscription_plan": "standard",
                "modules": "POS,Inventory",
                "base_sales": 11000,
                "volatility": 0.18,
                "activity_bias": 60,
            },
            {
                "legal_name": "Dammam Auto Care",
                "trade_name": "Auto Care Express",
                "city": "Dammam",
                "industry": "Services",
                "subscription_plan": "pro",
                "modules": "POS,Invoices",
                "base_sales": 9000,
                "volatility": 0.35,
                "activity_bias": 50,
            },
            {
                "legal_name": "Tabuk Home Supplies",
                "trade_name": "Home Supplies Tabuk",
                "city": "Tabuk",
                "industry": "Retail",
                "subscription_plan": "enterprise",
                "modules": "POS,Inventory,Invoices,Logistics",
                "base_sales": 17000,
                "volatility": 0.22,
                "activity_bias": 80,
            },
            {
                "legal_name": "Abha Coffee Collective",
                "trade_name": "Mountain Coffee",
                "city": "Abha",
                "industry": "F&B_Cafe",
                "subscription_plan": "standard",
                "modules": "POS,Inventory,Invoices",
                "base_sales": 7500,
                "volatility": 0.28,
                "activity_bias": 40,
            },
            {
                "legal_name": "Makkah Pharma Traders",
                "trade_name": "Medica",
                "city": "Makkah",
                "industry": "Pharma",
                "subscription_plan": "pro",
                "modules": "POS,Inventory,Invoices",
                "base_sales": 20000,
                "volatility": 0.15,
                "activity_bias": 75,
            },
            {
                "legal_name": "Al Khobar Logistics Hub",
                "trade_name": "CargoSwift",
                "city": "Al Khobar",
                "industry": "Logistics",
                "subscription_plan": "standard",
                "modules": "POS,Invoices",
                "base_sales": 12500,
                "volatility": 0.32,
                "activity_bias": 55,
            },
        ]

        today = date.today()
        for idx, info in enumerate(sample_customers, start=1):
            customer = Customer(
                legal_name=info["legal_name"],
                trade_name=info["trade_name"],
                cr_number=f"1010{idx:06d}",
                vat_number=f"310{idx:06d}00003",
                country="Saudi Arabia",
                city=info["city"],
                industry=info["industry"],
                founded_date=today.replace(year=today.year - randint(3, 8)),
                branches_count=randint(1, 5),
                acquisition_channel="silky_direct",
                referral_partner_id=None,
            )
            db.add(customer)
            db.flush()

            db.add(
                CustomerSetting(
                    customer_id=customer.id,
                    subscription_plan=info["subscription_plan"],
                    modules_enabled=info["modules"],
                    go_live_date=today.replace(year=today.year - randint(1, 3)),
                    status="active",
                )
            )

            users = _create_users(db, customer, roles=["manager", "cashier", "ops"])
            user_ids = [u.id for u in users]

            _seed_usage_events(db, customer, user_ids, activity_bias=info["activity_bias"])
            _seed_transactions(db, customer, base=info["base_sales"], volatility=info["volatility"])
            _seed_invoices(db, customer)

        db.commit()
    finally:
        db.close()
