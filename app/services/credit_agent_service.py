import json
import logging
from datetime import datetime
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import SilkyCreditProfileSnapshot
from ..schemas import CreditDashboard, LenderProfile
from .data_service import fetch_customer_kyc, fetch_usage_metrics, fetch_financial_metrics

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT = """
You are the **Silky Credit & Behaviour Intelligence Agent**, embedded inside Silky Systems.

Silky Systems is an all-in-one cloud platform (POS, ERP, logistics, growth) used by merchants
(F&B, FMCG, retail, logistics, manufacturing, etc.) to run their operations. You sit directly
on top of real transaction data, inventory, invoices, and usage logs.

Your job:
- Take structured features about ONE merchant (customer_id) from Silky Systems.
- Produce a SINGLE JSON object that matches EXACTLY the CreditDashboard schema below.
- Do NOT invent cross-customer data. Use only the provided features and context.
- If something cannot be computed, set the field to null and explain in data_quality_comment.

CreditDashboard ROOT-LEVEL STRUCTURE (REQUIRED fields at root):
{
  "customer_id": (int or str),
  "usage_mode": (one of: "internal_analytics", "bank_partner_portal", "merchant_portal"),
  "subscription_tier": (one of: "free", "standard", "pro", "enterprise"),
  "kyc_profile": {...},
  "behaviour_profile": {...},        ← REQUIRED top-level field
  "financial_health": {...},         ← REQUIRED top-level field
  "cashflow_forecast": {...},        ← REQUIRED top-level field
  "credit_analysis": {...},
  "safety_and_compliance": {...},
  "audit_metadata": {...},
  "available_offers": [...],
  "early_warning_flags": [...],
  "recommendations_for_lender": [...],
  "improvement_actions_for_merchant": [...],
  "segment_specific_strengths": [...],
  "segment_specific_risks": [...],
  "economics": {...} (optional)
}

REQUIRED NESTED STRUCTURES:

behaviour_profile:
{
  "activity": {
    "status": ("active" | "at_risk" | "inactive"),
    "active_days_last_90": (int),
    "logins_last_90": (int),
    "active_users": (int),
    "total_users": (int)
  },
  "feature_adoption": [{"module": str, "usage_level": str, "key_metrics": {...}}],
  "discipline": {"invoice_matching_rate": float, "stock_update_frequency": str, ...},
  "behaviour_risks": [...]
}

financial_health:
{
  "revenue": {
    "avg_monthly_revenue": float,
    "revenue_trend": ("growing" | "stable" | "declining" | "volatile" | "unknown"),
    "growth_rate_yoy": float (optional),
    "growth_rate_mom": float (optional),
    "revenue_volatility_score": float (optional)
  },
  "profitability_proxy": {"gross_margin_percent": float (optional), "comment": str (optional)},
  "liquidity": {"avg_dso_days": float (optional), "avg_dpo_days": float (optional), ...},
  "concentration": {"revenue_concentration_comment": str (optional), "top_customer_share": float (optional)},
  "seasonality": {"has_strong_seasonality": bool, "seasonality_comment": str (optional)}
}

cashflow_forecast:
{
  "base_case": {
    "currency": "SAR" (or appropriate),
    "net_cash_flow_next_3_months": float,
    "net_cash_flow_next_12_months": float
  },
  "conservative_case": {...},  ← Same structure as base_case
  "optimistic_case": {...},     ← Same structure as base_case
  "confidence_level": ("low" | "medium" | "high"),
  "key_drivers": [...]
}

credit_analysis (MUST INCLUDE max_safe_tenor_months):
{
  "credit_score": int (0-100),
  "credit_band": ("A+" | "A" | "B" | "C" | "D"),
  "recommended_credit_limit": {
    "amount": float,
    "currency": "SAR",
    "logic_comment": str (optional)
  },
  "max_safe_tenor_months": int,           ← REQUIRED
  "score_explanation": {
    "positive_drivers": [...],
    "risk_factors": [...]
  },
  "data_quality_comment": str (optional)
}

Scoring principles:
- credit_score: 0–100. A+ ≥ 90, A 80–89, B 70–79, C 60–69, D < 60.
- recommended_credit_limit: Typically 20–40% of avg monthly revenue, adjusted for risk.
- max_safe_tenor_months: Typically 6–24 months depending on score and industry.
- positive_drivers and risk_factors: List top 3–5 each.

Safety & governance:
- used_sensitive_attributes = false (never use religion, gender, ethnicity, nationality).
- regulatory_flags: List data gaps, limitations, or assumptions.
- audit_metadata: Include model_version, model_provider, generated_at (ISO format).

Views:
- internal_analytics: Maximum detail, direct language.
- bank_partner_portal: Formal, bank-appropriate language.
- merchant_portal: Coaching tone, actionable improvements.

CRITICAL: Return ONLY valid JSON. Do not add markdown, code blocks, or explanations.
"""


def _derive_usage_mode(viewer_type: str, usage_mode: Optional[str]) -> str:
    if usage_mode:
        return usage_mode
    if viewer_type == "silky_internal":
        return "internal_analytics"
    if viewer_type == "bank_partner":
        return "bank_partner_portal"
    if viewer_type == "merchant":
        return "merchant_portal"
    return "internal_analytics"


def _infer_subscription_tier(
    subscription_tier: Optional[str],
    kyc: Dict[str, Any],
) -> str:
    if subscription_tier:
        return subscription_tier
    plan = (kyc.get("relationship_with_silky") or {}).get("subscription_plan") or ""
    plan = plan.lower()
    if "pro" in plan or "enterprise" in plan:
        return "pro"
    if "standard" in plan:
        return "standard"
    if "free" in plan or "trial" in plan:
        return "free"
    return "standard"


def _build_lender_profile(lender_id: Optional[str], segment: Optional[str]) -> Optional[LenderProfile]:
    if not lender_id:
        return None

    # Generic, conservative defaults. Banks can refine these rules later.
    allowed_segments = [segment] if segment else []
    profile = LenderProfile(
        lender_id=lender_id,
        allowed_segments=allowed_segments,
        min_score=60,
        max_exposure_per_customer=1_000_000.0,
        max_tenor_months=24,
        pricing_strategy="base_rate_plus_margin_by_band",
    )
    return profile


def _coerce_model_output(data: Dict[str, Any]) -> None:
    """
    Normalize model output to match CreditDashboard schema.
    Modifies `data` in-place to fix common mismatches.
    """
    # Fix available_offers: map `type` → `product_type`, `max_amount` → `amount`, `suggested_tenor_months` → `tenor_months`
    if "available_offers" in data and isinstance(data["available_offers"], list):
        for offer in data["available_offers"]:
            if "type" in offer and "product_type" not in offer:
                # Map common model offer type names to CreditOffer product_type enum
                type_map = {
                    "working_capital_term_loan": "working_capital_loan",
                    "supplier_payments_line": "working_capital_loan",
                    "invoice_factoring": "invoice_factoring",
                    "invoice_financing": "invoice_factoring",
                    "invoice_financing_limit": "invoice_factoring",
                    "terminal_financing": "terminal_financing",
                    "overdraft": "overdraft",
                    "card_limit": "card_limit",
                }
                offer["product_type"] = type_map.get(offer["type"], "other")
            if "max_amount" in offer and "amount" not in offer:
                offer["amount"] = offer.pop("max_amount")
            if "suggested_tenor_months" in offer and "tenor_months" not in offer:
                offer["tenor_months"] = offer.pop("suggested_tenor_months")
            # Clean up extra fields to avoid Pydantic errors
            for extra_key in ["type", "intended_use", "pricing_apr", "purpose", "eligibility_comment"]:
                offer.pop(extra_key, None)

    # Fix list fields that should contain strings, not objects.
    # Extract description/text/recommendation/action from nested objects.
    def flatten_list_to_strings(items: Any) -> List[str]:
        """Convert a list of strings or objects to a list of strings."""
        result = []
        if not isinstance(items, list):
            return result
        for item in items:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Try common keys for extracting text (including "strength", "risk", "detail")
                text = (item.get("description") or item.get("recommendation") or item.get("action") 
                        or item.get("text") or item.get("comment") or item.get("code")
                        or item.get("strength") or item.get("risk") or item.get("detail"))
                if text:
                    result.append(text)
        return result

    for field_name in ["early_warning_flags", "recommendations_for_lender", "improvement_actions_for_merchant",
                       "segment_specific_strengths", "segment_specific_risks"]:
        if field_name in data:
            fixed = flatten_list_to_strings(data[field_name])
            if fixed:
                data[field_name] = fixed

    # Ensure subscription_tier is present and valid
    if "subscription_tier" not in data or data["subscription_tier"] not in ["free", "standard", "pro", "enterprise"]:
        data["subscription_tier"] = "standard"

    # Remove extra/unknown root fields that Pydantic won't accept
    schema_fields = {
        "customer_id", "usage_mode", "subscription_tier", "kyc_profile", "behaviour_profile",
        "financial_health", "cashflow_forecast", "credit_analysis", "safety_and_compliance",
        "audit_metadata", "available_offers", "early_warning_flags", "recommendations_for_lender",
        "improvement_actions_for_merchant", "segment_specific_strengths", "segment_specific_risks",
        "lender_profile", "economics"
    }
    for key in list(data.keys()):
        if key not in schema_fields:
            data.pop(key, None)


def _get_cached_dashboard(
    db: Session,
    customer_id: int,
    viewer_type: str,
    usage_mode: str,
    subscription_tier: str,
    lender_id: Optional[str],
) -> Optional[CreditDashboard]:
    """Return a cached snapshot if one already exists for this view."""

    lender_clause = (
        SilkyCreditProfileSnapshot.lender_id.is_(None)
        if lender_id is None
        else SilkyCreditProfileSnapshot.lender_id == lender_id
    )

    snapshot = (
        db.query(SilkyCreditProfileSnapshot)
        .filter(
            SilkyCreditProfileSnapshot.customer_id == customer_id,
            SilkyCreditProfileSnapshot.viewer_type == viewer_type,
            SilkyCreditProfileSnapshot.usage_mode == usage_mode,
            SilkyCreditProfileSnapshot.subscription_tier == subscription_tier,
            lender_clause,
        )
        .order_by(SilkyCreditProfileSnapshot.snapshot_at.desc())
        .first()
    )

    if not snapshot:
        return None

    try:
        return CreditDashboard.model_validate_json(snapshot.dashboard_json)
    except ValidationError:
        return None


def generate_dashboard_for_customer(
    db: Session,
    customer_id: int,
    viewer_type: Literal["silky_internal", "bank_partner", "merchant"] = "silky_internal",
    usage_mode: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    lender_id: Optional[str] = None,
) -> CreditDashboard:
    """Main pipeline:

    - Fetch features from the Silky database.
    - Build a structured features dict for the model.
    - Call OpenAI Responses API with JSON schema (CreditDashboard).
    - Persist snapshot.
    - Return the dashboard object.
    """
    logger.info("Generating credit dashboard for customer_id=%s viewer_type=%s", customer_id, viewer_type)

    kyc = fetch_customer_kyc(db, customer_id)
    usage_metrics = fetch_usage_metrics(db, customer_id)
    financial_metrics = fetch_financial_metrics(db, customer_id)

    resolved_usage_mode = _derive_usage_mode(viewer_type, usage_mode)
    resolved_subscription_tier = _infer_subscription_tier(subscription_tier, kyc)

    cached = _get_cached_dashboard(
        db=db,
        customer_id=customer_id,
        viewer_type=viewer_type,
        usage_mode=resolved_usage_mode,
        subscription_tier=resolved_subscription_tier,
        lender_id=lender_id,
    )
    if cached:
        logger.info(
            "Returning cached dashboard for customer_id=%s viewer_type=%s",
            customer_id,
            viewer_type,
        )
        return cached

    segment = kyc.get("segment")
    lender_profile = _build_lender_profile(lender_id, segment)

    features: Dict[str, Any] = {
        "customer_id": customer_id,
        "viewer_type": viewer_type,
        "usage_mode": resolved_usage_mode,
        "subscription_tier": resolved_subscription_tier,
        "openai_model": settings.openai_model,
        "kyc": kyc,
        "usage_metrics": usage_metrics,
        "financial_metrics": financial_metrics,
        "lender_profile": lender_profile.model_dump() if lender_profile else None,
    }

    if financial_metrics.get("revenue_period"):
        features["input_data_date_range"] = financial_metrics["revenue_period"]

    prompt = f"""{SYSTEM_PROMPT}

You are generating a CreditDashboard for customer_id={customer_id}.

INPUT DATA from Silky Systems:
```json
{json.dumps(features, default=str)}
```

TASK:
1. Generate a complete CreditDashboard JSON object that matches ALL the required structures defined above.
2. Map input data into the correct nested structure:
   - behaviour_profile: Derive from usage_metrics (active_days_last_90, logins, feature_adoption).
   - financial_health: Derive from financial_metrics (revenue, trend, liquidity, concentration, seasonality).
   - cashflow_forecast: Generate base/conservative/optimistic scenarios based on revenue volatility.
   - credit_analysis: Score (0–100), band (A+ | A | B | C | D), recommended_credit_limit, max_safe_tenor_months, offers.
   - safety_and_compliance & audit_metadata: Fill with appropriate metadata and disclaimers.
3. Ensure ALL root-level required fields present: customer_id, usage_mode, subscription_tier, kyc_profile, behaviour_profile, financial_health, cashflow_forecast, credit_analysis, safety_and_compliance, audit_metadata.
4. Ensure credit_analysis.max_safe_tenor_months is always present (typically 6–24 months).
5. Tailor recommendations, flags, and insights to the merchant's segment and viewer_type.
6. For missing data, set to null/empty and document in data_quality_comment and regulatory_flags.

Return ONLY valid JSON. No markdown, code blocks, explanations, or extra text.
"""

    logger.debug("Calling OpenAI Responses API for customer_id=%s", customer_id)

    # The OpenAI Python SDK Responses.create does not accept a `response_format`
    # keyword in this installation. Send the prompt as `input` and parse the
    # JSON returned in the text output. If you want stricter enforcement, use
    # any available SDK parameter for JSON schema in your SDK version or
    # validate the parsed JSON against the Pydantic model (done below).
    response = client.responses.create(
        model=settings.openai_model,
        input=prompt,
    )

    # The structured JSON is returned as text in the first output item.
    raw_json = response.output[0].content[0].text
    data = json.loads(raw_json)

    # Coerce model output to match CreditDashboard schema, fixing common mismatches
    _coerce_model_output(data)

    try:
        dashboard = CreditDashboard.model_validate(data)
    except ValidationError as e:
        # Log detailed validation errors and the raw model output to help
        # debugging. Raise a ValueError so the API layer can return a clear
        # error to the caller instead of a generic 500/422.
        logger.error(
            "CreditDashboard validation failed for customer_id=%s: %s",
            customer_id,
            e.errors(),
        )
        logger.debug("Raw model output: %s", raw_json)
        raise ValueError(
            f"Model output did not match CreditDashboard schema: {e.errors()}. Raw output: {raw_json}"
        )

    logger.info(
        "Generated dashboard for customer_id=%s: score=%s band=%s",
        customer_id,
        dashboard.credit_analysis.credit_score,
        dashboard.credit_analysis.credit_band,
    )

    # Persist snapshot for monitoring and audit.
    snapshot = SilkyCreditProfileSnapshot(
        customer_id=int(dashboard.customer_id),
        snapshot_at=datetime.utcnow(),
        viewer_type=viewer_type,
        usage_mode=dashboard.usage_mode,
        subscription_tier=dashboard.subscription_tier,
        lender_id=lender_id,
        dashboard_json=dashboard.model_dump_json(),
        credit_score=dashboard.credit_analysis.credit_score,
        credit_band=dashboard.credit_analysis.credit_band,
        recommended_credit_limit_amount=dashboard.credit_analysis.recommended_credit_limit.amount,
        recommended_credit_limit_currency=dashboard.credit_analysis.recommended_credit_limit.currency,
        max_safe_tenor_months=dashboard.credit_analysis.max_safe_tenor_months,
        data_quality_comment=dashboard.credit_analysis.data_quality_comment,
        model_version=settings.openai_model,
        model_provider="openai-chatgpt-5.1",
        input_data_date_range=features.get("input_data_date_range"),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return dashboard
