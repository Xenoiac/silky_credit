from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


# --- KYC & Relationship ---


class Registration(BaseModel):
    cr_number: Optional[str] = None
    vat_number: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    years_in_business: Optional[int] = None


class RelationshipWithSilky(BaseModel):
    go_live_date: Optional[str] = None
    subscription_plan: Optional[str] = None
    modules_enabled: List[str] = Field(default_factory=list)
    tenure_months: Optional[int] = None
    silky_payment_behaviour: Optional[Literal["on_time", "occasional_late", "chronic_late", "unknown"]] = "unknown"


class KYCProfile(BaseModel):
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    registration: Registration
    segment: Optional[str] = None
    branches_count: Optional[int] = None
    acquisition_channel: Optional[str] = None
    referral_partner_id: Optional[str] = None
    relationship_with_silky: RelationshipWithSilky


# --- Behaviour ---


class BehaviourActivity(BaseModel):
    status: Literal["active", "at_risk", "inactive"]
    active_days_last_90: int
    logins_last_90: int
    active_users: int
    total_users: int


class FeatureAdoptionItem(BaseModel):
    module: str
    usage_level: Literal["low", "medium", "high"]
    key_metrics: dict


class BehaviourDiscipline(BaseModel):
    invoice_matching_rate: Optional[float] = None
    stock_update_frequency: Optional[str] = None
    data_completeness_score: Optional[float] = None


class BehaviourProfile(BaseModel):
    activity: BehaviourActivity
    feature_adoption: List[FeatureAdoptionItem]
    discipline: BehaviourDiscipline
    behaviour_risks: List[str] = Field(default_factory=list)


# --- Financial Health ---


class RevenueInfo(BaseModel):
    avg_monthly_revenue: float
    revenue_trend: Literal["growing", "stable", "declining", "volatile", "unknown"]
    growth_rate_yoy: Optional[float] = None
    growth_rate_mom: Optional[float] = None
    revenue_volatility_score: Optional[float] = None


class ProfitabilityProxy(BaseModel):
    gross_margin_percent: Optional[float] = None
    comment: Optional[str] = None


class LiquidityInfo(BaseModel):
    avg_dso_days: Optional[float] = None
    avg_dpo_days: Optional[float] = None
    cash_conversion_cycle_days: Optional[float] = None
    overdue_invoices_ratio: Optional[float] = None


class ConcentrationInfo(BaseModel):
    revenue_concentration_comment: Optional[str] = None
    top_customer_share: Optional[float] = None


class SeasonalityInfo(BaseModel):
    has_strong_seasonality: bool
    seasonality_comment: Optional[str] = None


class FinancialHealth(BaseModel):
    revenue: RevenueInfo
    profitability_proxy: ProfitabilityProxy
    liquidity: LiquidityInfo
    concentration: ConcentrationInfo
    seasonality: SeasonalityInfo


# --- Cashflow ---


class CashflowScenario(BaseModel):
    currency: str = "SAR"
    net_cash_flow_next_3_months: float
    net_cash_flow_next_12_months: float


class CashflowForecast(BaseModel):
    base_case: CashflowScenario
    conservative_case: CashflowScenario
    optimistic_case: CashflowScenario
    confidence_level: Literal["low", "medium", "high"]
    key_drivers: List[str]


# --- Credit Offers & Analysis ---


class CreditOffer(BaseModel):
    offer_id: str
    product_type: Literal[
        "working_capital_loan",
        "invoice_factoring",
        "terminal_financing",
        "overdraft",
        "card_limit",
        "other",
    ]
    amount: float
    currency: str = "SAR"
    tenor_months: int
    interest_rate_percent: Optional[float] = None
    fee_percent: Optional[float] = None
    grace_period_days: Optional[int] = None
    collateral_required: bool = False
    collateral_description: Optional[str] = None
    conditions_precedent: List[str] = Field(default_factory=list)
    risk_tier: Literal["A", "B", "C"] = "B"


class RecommendedCreditLimit(BaseModel):
    amount: float
    currency: str = "SAR"
    logic_comment: Optional[str] = None


class ScoreExplanation(BaseModel):
    positive_drivers: List[str]
    risk_factors: List[str]


class CreditAnalysis(BaseModel):
    credit_score: int  # 0-100
    credit_band: Literal["A+", "A", "B", "C", "D"]
    recommended_credit_limit: RecommendedCreditLimit
    max_safe_tenor_months: int
    score_explanation: ScoreExplanation
    data_quality_comment: Optional[str] = None


# --- Safety, Audit, Economics ---


class SafetyCompliance(BaseModel):
    used_sensitive_attributes: bool
    notes: Optional[str] = None
    regulatory_flags: List[str] = Field(default_factory=list)


class AuditMetadata(BaseModel):
    model_version: str
    model_provider: str = "openai-chatgpt-5.1"
    input_data_date_range: Optional[str] = None
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EconomicsInfo(BaseModel):
    estimated_annual_revenue_to_silky: Optional[float] = None
    estimated_annual_revenue_to_lender: Optional[float] = None
    economics_comment: Optional[str] = None


# --- Lender Profile ---


class LenderProfile(BaseModel):
    lender_id: str
    allowed_segments: List[str] = Field(default_factory=list)
    min_score: Optional[int] = None
    max_exposure_per_customer: Optional[float] = None
    max_tenor_months: Optional[int] = None
    pricing_strategy: Optional[str] = None


# --- Root Dashboard ---


class CreditDashboard(BaseModel):
    customer_id: Union[str, int]
    kyc_profile: KYCProfile
    behaviour_profile: BehaviourProfile
    financial_health: FinancialHealth
    cashflow_forecast: CashflowForecast
    credit_analysis: CreditAnalysis
    safety_and_compliance: SafetyCompliance

    # Business & monitoring extensions
    available_offers: List[CreditOffer] = Field(default_factory=list)
    early_warning_flags: List[str] = Field(default_factory=list)
    recommendations_for_lender: List[str] = Field(default_factory=list)
    improvement_actions_for_merchant: List[str] = Field(default_factory=list)
    segment_specific_strengths: List[str] = Field(default_factory=list)
    segment_specific_risks: List[str] = Field(default_factory=list)
    audit_metadata: AuditMetadata
    economics: Optional[EconomicsInfo] = None

    # View & configuration
    usage_mode: Literal[
        "internal_analytics",
        "merchant_portal",
        "bank_partner_portal",
    ]
    subscription_tier: Literal["free", "standard", "pro", "enterprise"]
    lender_profile: Optional[LenderProfile] = None
