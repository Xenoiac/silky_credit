from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from ..models import Customer, PosTransaction, Invoice, UsageEvent, User


def _get_customer_or_raise(db: Session, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError(f"Customer {customer_id} not found")
    return customer


def fetch_customer_kyc(db: Session, customer_id: int) -> Dict[str, Any]:
    customer = _get_customer_or_raise(db, customer_id)
    settings = customer.settings

    today = date.today()
    years_in_business = None
    if customer.founded_date:
        years_in_business = today.year - customer.founded_date.year

    go_live_date = settings.go_live_date if settings else None
    tenure_months = None
    if go_live_date:
        diff = relativedelta(today, go_live_date)
        tenure_months = diff.years * 12 + diff.months

    modules: List[str] = []
    if settings and settings.modules_enabled:
        modules = [m.strip() for m in settings.modules_enabled.split(",") if m.strip()]

    kyc = {
        "legal_name": customer.legal_name,
        "trade_name": customer.trade_name,
        "registration": {
            "cr_number": customer.cr_number,
            "vat_number": customer.vat_number,
            "country": customer.country,
            "city": customer.city,
            "years_in_business": years_in_business,
        },
        "segment": customer.industry,
        "branches_count": customer.branches_count,
        "acquisition_channel": customer.acquisition_channel,
        "referral_partner_id": customer.referral_partner_id,
        "relationship_with_silky": {
            "go_live_date": go_live_date.isoformat() if go_live_date else None,
            "subscription_plan": settings.subscription_plan if settings else None,
            "modules_enabled": modules,
            "tenure_months": tenure_months,
            "silky_payment_behaviour": "unknown",
        },
    }
    return kyc


def fetch_usage_metrics(db: Session, customer_id: int) -> Dict[str, Any]:
    _ = _get_customer_or_raise(db, customer_id)

    cutoff = datetime.utcnow() - timedelta(days=90)

    events: List[UsageEvent] = (
        db.query(UsageEvent)
        .filter(
            UsageEvent.customer_id == customer_id,
            UsageEvent.timestamp >= cutoff,
        )
        .all()
    )

    active_days = len({evt.timestamp.date() for evt in events})
    total_events = len(events)
    active_users_ids = {evt.user_id for evt in events if evt.user_id is not None}

    total_users = (
        db.query(User).filter(User.customer_id == customer_id).count()
    )

    if active_days > 20:
        status = "active"
    elif active_days > 5:
        status = "at_risk"
    else:
        status = "inactive"

    module_counter: Counter = Counter(evt.module for evt in events)
    feature_adoption: List[Dict[str, Any]] = []
    for module, count in module_counter.items():
        if count > 3000:
            usage_level = "high"
        elif count > 500:
            usage_level = "medium"
        else:
            usage_level = "low"
        feature_adoption.append(
            {
                "module": module,
                "usage_level": usage_level,
                "key_metrics": {
                    "events_last_90": count,
                },
            }
        )

    usage = {
        "activity": {
            "status": status,
            "active_days_last_90": active_days,
            "logins_last_90": total_events,
            "active_users": len(active_users_ids),
            "total_users": total_users,
        },
        "feature_adoption": feature_adoption,
        # discipline is left partly for the agent to infer; we can add crude placeholders.
    }
    return usage


def fetch_financial_metrics(db: Session, customer_id: int) -> Dict[str, Any]:
    _ = _get_customer_or_raise(db, customer_id)

    today = date.today()
    since = today - relativedelta(months=24)

    txs: List[PosTransaction] = (
        db.query(PosTransaction)
        .filter(
            PosTransaction.customer_id == customer_id,
            PosTransaction.date >= since,
        )
        .all()
    )

    invoices: List[Invoice] = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer_id,
            Invoice.issue_date >= since,
        )
        .all()
    )

    # Group revenue by month (YYYY-MM-01)
    monthly_revenue: Dict[str, float] = {}
    for tx in txs:
        month_key = tx.date.replace(day=1).isoformat()
        monthly_revenue[month_key] = monthly_revenue.get(month_key, 0.0) + float(tx.net_sales or 0.0)

    # Sort months
    sorted_months = sorted(monthly_revenue.keys())
    monthly_revenue_list: List[Dict[str, Any]] = [
        {"month": m, "revenue": round(monthly_revenue[m], 2)} for m in sorted_months
    ]
    revenues = [m["revenue"] for m in monthly_revenue_list]

    if revenues:
        avg_monthly = sum(revenues) / len(revenues)
    else:
        avg_monthly = 0.0

    last = revenues[-1] if revenues else 0.0
    prev = revenues[-2] if len(revenues) > 1 else last
    mom_growth = (last - prev) / prev if prev > 0 else 0.0

    # Build invoice list & simple liquidity approximations
    invoice_dicts: List[Dict[str, Any]] = []
    overdue_count = 0
    for inv in invoices:
        is_overdue = inv.status == "overdue"
        if is_overdue:
            overdue_count += 1

        invoice_dicts.append(
            {
                "id": inv.id,
                "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "amount": float(inv.amount),
                "status": inv.status,
                "paid_date": inv.paid_date.isoformat() if inv.paid_date else None,
            }
        )

    overdue_ratio = overdue_count / len(invoices) if invoices else 0.0

    revenue_period = None
    if sorted_months:
        revenue_period = f"{sorted_months[0]} to {sorted_months[-1]}"

    financial = {
        "monthly_revenue": monthly_revenue_list,
        "avg_monthly_revenue": avg_monthly,
        "mom_growth": mom_growth,
        "invoices": invoice_dicts,
        "overdue_invoices_ratio": overdue_ratio,
        "revenue_period": revenue_period,
    }
    return financial
