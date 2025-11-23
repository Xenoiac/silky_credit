import logging
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import CreditDashboard, CustomerSummary
from .services.credit_agent_service import generate_dashboard_for_customer
from .services.data_service import list_customers_with_latest_credit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/credit-dashboard/{customer_id}",
    response_model=CreditDashboard,
    summary="Generate credit & behaviour dashboard for a Silky customer",
)
def get_credit_dashboard(
    customer_id: int,
    viewer_type: Literal["silky_internal", "bank_partner", "merchant"] = Query(
        "silky_internal",
        description="Type of viewer: silky_internal, bank_partner, merchant",
    ),
    usage_mode: Optional[
        Literal["internal_analytics", "merchant_portal", "bank_partner_portal"]
    ] = Query(
        None,
        description="Optional explicit usage mode; default derived from viewer_type",
    ),
    subscription_tier: Optional[Literal["free", "standard", "pro", "enterprise"]] = Query(
        None,
        description="Optional subscription tier; default inferred from customer settings",
    ),
    lender_id: Optional[str] = Query(
        None,
        description="Optional lender identifier (e.g. SAB, ANB).",
    ),
    db: Session = Depends(get_db),
):
    try:
        dashboard = generate_dashboard_for_customer(
            db=db,
            customer_id=customer_id,
            viewer_type=viewer_type,
            usage_mode=usage_mode,
            subscription_tier=subscription_tier,
            lender_id=lender_id,
        )
        return dashboard
    except ValueError as e:
        # Treat model output/schema mismatches as a 502 Bad Gateway since the
        # upstream model produced an invalid response.
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate credit dashboard")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/api/customers",
    response_model=List[CustomerSummary],
    summary="List customers with latest credit snapshot",
)
def get_customers(db: Session = Depends(get_db)):
    try:
        return list_customers_with_latest_credit(db)
    except Exception:
        logger.exception("Failed to list customers")
        raise HTTPException(status_code=500, detail="Internal server error")


_DASHBOARD_HTML = (Path(__file__).resolve().parent / "static" / "dashboard.html").read_text()


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page() -> str:
    return _DASHBOARD_HTML
