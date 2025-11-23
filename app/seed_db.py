from datetime import date, datetime, timedelta
from random import randint, uniform

from .db import Base, engine, SessionLocal
from .models import (
    Customer,
    CustomerSetting,
    User,
    UsageEvent,
    PosTransaction,
    Invoice,
)


def seed_database() -> None:
    """Create tables and seed a small demo dataset if DB is empty."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # If there is already a customer, assume seeded.
        if db.query(Customer).first():
            return

        # Create one demo customer
        customer = Customer(
            legal_name="Riyadh Burger House Co.",
            trade_name="Burger House - Riyadh",
            cr_number="1010123456",
            vat_number="310123456700003",
            country="Saudi Arabia",
            city="Riyadh",
            industry="F&B_QSR",
            founded_date=date.today().replace(year=date.today().year - 5),
            branches_count=3,
            acquisition_channel="silky_direct",
            referral_partner_id=None,
        )
        db.add(customer)
        db.flush()

        settings = CustomerSetting(
            customer_id=customer.id,
            subscription_plan="pro",
            modules_enabled="POS,Inventory,Invoices",
            go_live_date=date.today().replace(year=date.today().year - 2),
            status="active",
        )
        db.add(settings)

        # Create a few users
        users = [
            User(customer_id=customer.id, name="Store Manager", role="manager"),
            User(customer_id=customer.id, name="Cashier 1", role="cashier"),
            User(customer_id=customer.id, name="Cashier 2", role="cashier"),
        ]
        db.add_all(users)
        db.flush()

        user_ids = [u.id for u in users]

        # Usage events for last 90 days
        now = datetime.utcnow()
        for day_offset in range(0, 90):
            day = now - timedelta(days=day_offset)
            # Simulate activity on ~40 days out of 90
            if randint(0, 100) < 45:
                for _ in range(randint(5, 20)):
                    evt = UsageEvent(
                        customer_id=customer.id,
                        user_id=user_ids[randint(0, len(user_ids) - 1)],
                        module="POS",
                        event_type="login",
                        timestamp=day - timedelta(minutes=randint(0, 600)),
                    )
                    db.add(evt)
                # Some inventory events
                for _ in range(randint(1, 5)):
                    evt = UsageEvent(
                        customer_id=customer.id,
                        user_id=user_ids[randint(0, len(user_ids) - 1)],
                        module="Inventory",
                        event_type="stock_update",
                        timestamp=day - timedelta(minutes=randint(0, 600)),
                    )
                    db.add(evt)

        # POS transactions for last 12 months
        today = date.today()
        for month_offset in range(0, 12):
            # Approximate first day of month by subtracting 30-day blocks
            month_start = today - timedelta(days=month_offset * 30)
            for _ in range(20):
                sales = round(uniform(3000, 15000), 2)
                tx = PosTransaction(
                    customer_id=customer.id,
                    date=month_start - timedelta(days=randint(0, 25)),
                    net_sales=sales,
                    branch_id=randint(1, customer.branches_count),
                    payment_method="card",
                )
                db.add(tx)

        # Invoices for last 6 months
        for month_offset in range(0, 6):
            month_start = today - timedelta(days=month_offset * 30)
            for _ in range(5):
                issue = month_start - timedelta(days=randint(0, 10))
                due = issue + timedelta(days=30)
                amount = round(uniform(5000, 20000), 2)
                # Some invoices paid, some overdue
                if randint(0, 100) < 75:
                    status = "paid"
                    paid_date = due + timedelta(days=randint(-5, 10))
                else:
                    status = "overdue"
                    paid_date = None

                inv = Invoice(
                    customer_id=customer.id,
                    issue_date=issue,
                    due_date=due,
                    amount=amount,
                    status=status,
                    paid_date=paid_date,
                )
                db.add(inv)

        db.commit()
    finally:
        db.close()
