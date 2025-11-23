import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import CreditDashboard
from .services.credit_agent_service import generate_dashboard_for_customer

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
