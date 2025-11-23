import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeContent:
    def __init__(self, text: str):
        self.text = text


class _FakeOutput:
    def __init__(self, text: str):
        self.content = [_FakeContent(text)]


class _FakeResponse:
    def __init__(self, text: str):
        self.output = [_FakeOutput(text)]


def _stub_dashboard_payload() -> dict[str, Any]:
    return {
        "customer_id": 1,
        "usage_mode": "internal_analytics",
        "subscription_tier": "standard",
        "kyc_profile": {
            "legal_name": "Test Co",
            "trade_name": "Test Co",
            "registration": {
                "cr_number": "123",
                "vat_number": "456",
                "country": "SA",
                "city": "Riyadh",
                "years_in_business": 5,
            },
            "segment": "F&B_QSR",
            "branches_count": 2,
            "acquisition_channel": "silky_direct",
            "referral_partner_id": None,
            "relationship_with_silky": {
                "go_live_date": "2022-01-01",
                "subscription_plan": "pro",
                "modules_enabled": ["POS", "Inventory"],
                "tenure_months": 24,
                "silky_payment_behaviour": "on_time",
            },
        },
        "behaviour_profile": {
            "activity": {
                "status": "active",
                "active_days_last_90": 30,
                "logins_last_90": 120,
                "active_users": 3,
                "total_users": 3,
            },
            "feature_adoption": [
                {"module": "POS", "usage_level": "high", "key_metrics": {"events_last_90": 120}},
            ],
            "discipline": {
                "invoice_matching_rate": 0.92,
                "stock_update_frequency": "weekly",
                "data_completeness_score": 0.9,
            },
            "behaviour_risks": ["Late-night logins"],
        },
        "financial_health": {
            "revenue": {
                "avg_monthly_revenue": 12000.0,
                "revenue_trend": "growing",
                "growth_rate_yoy": 0.15,
                "growth_rate_mom": 0.04,
                "revenue_volatility_score": 0.2,
            },
            "profitability_proxy": {"gross_margin_percent": 42.0, "comment": "Healthy"},
            "liquidity": {
                "avg_dso_days": 28.0,
                "avg_dpo_days": 35.0,
                "cash_conversion_cycle_days": -7.0,
                "overdue_invoices_ratio": 0.1,
            },
            "concentration": {"revenue_concentration_comment": "Diversified", "top_customer_share": 0.3},
            "seasonality": {"has_strong_seasonality": False, "seasonality_comment": "Stable"},
        },
        "cashflow_forecast": {
            "base_case": {
                "currency": "SAR",
                "net_cash_flow_next_3_months": 50000.0,
                "net_cash_flow_next_12_months": 200000.0,
            },
            "conservative_case": {
                "currency": "SAR",
                "net_cash_flow_next_3_months": 30000.0,
                "net_cash_flow_next_12_months": 120000.0,
            },
            "optimistic_case": {
                "currency": "SAR",
                "net_cash_flow_next_3_months": 70000.0,
                "net_cash_flow_next_12_months": 260000.0,
            },
            "confidence_level": "medium",
            "key_drivers": ["Stable POS throughput"],
        },
        "credit_analysis": {
            "credit_score": 85,
            "credit_band": "A",
            "recommended_credit_limit": {
                "amount": 4000.0,
                "currency": "SAR",
                "logic_comment": "~33% of average monthly revenue",
            },
            "max_safe_tenor_months": 12,
            "score_explanation": {
                "positive_drivers": ["Growing revenue", "Healthy margins"],
                "risk_factors": ["Moderate volatility"],
            },
            "data_quality_comment": "Synthetic data for test",
        },
        "safety_and_compliance": {
            "used_sensitive_attributes": False,
            "notes": "", 
            "regulatory_flags": [],
        },
        "available_offers": [],
        "early_warning_flags": [],
        "recommendations_for_lender": [],
        "improvement_actions_for_merchant": [],
        "segment_specific_strengths": [],
        "segment_specific_risks": [],
        "audit_metadata": {
            "model_version": "gpt-test",
            "model_provider": "openai-chatgpt-5.1",
            "input_data_date_range": "2023-01 to 2023-12",
            "generated_at": "2024-01-01T00:00:00",
        },
        "economics": {
            "estimated_annual_revenue_to_silky": 10000.0,
            "estimated_annual_revenue_to_lender": 45000.0,
            "economics_comment": "Healthy LTV",
        },
        "lender_profile": None,
    }


def _create_test_app(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("DB_URL", "sqlite:///./test_unit.db")

    import app.config as config
    importlib.reload(config)
    import app.db as db
    importlib.reload(db)
    import app.seed_db as seed_db
    importlib.reload(seed_db)
    import app.services.credit_agent_service as credit_agent_service
    importlib.reload(credit_agent_service)

    # Stub the OpenAI responses client
    def _fake_create(model: str, input: str):
        payload = _stub_dashboard_payload()
        return _FakeResponse(json.dumps(payload))

    monkeypatch.setattr(credit_agent_service.client.responses, "create", _fake_create)

    import main as main_module
    importlib.reload(main_module)

    seed_db.seed_database()
    return TestClient(main_module.create_app())


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    with _create_test_app(monkeypatch) as client:
        yield client


def test_customers_endpoint_returns_seeded_customer(client: TestClient):
    resp = client.get("/api/customers")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert first["legal_name"]
    assert "latest_credit" in first


def test_credit_dashboard_generation(client: TestClient):
    resp = client.get("/api/credit-dashboard/1")
    assert resp.status_code == 200

    body = resp.json()
    assert body["credit_analysis"]["credit_score"] == 85
    assert body["credit_analysis"]["credit_band"] == "A"

    refreshed = client.get("/api/customers").json()
    assert refreshed[0]["latest_credit"]["credit_band"] == "A"


def test_dashboard_page_served(client: TestClient):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Customer Credit Universe" in resp.text
