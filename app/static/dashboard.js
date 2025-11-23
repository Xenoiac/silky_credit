const state = {
    customers: [],
    selectedId: null,
    dashboard: null,
    charts: {
        revenue: null,
        cashflow: null,
    },
};

const els = {
    status: document.getElementById('app-status'),
    customerList: document.getElementById('customer-list'),
    viewer: document.getElementById('viewer-select'),
    tier: document.getElementById('tier-input'),
    lender: document.getElementById('lender-input'),
    generate: document.getElementById('generate-btn'),
    refresh: document.getElementById('refresh-btn'),
    loadingChip: document.getElementById('loading-chip'),
    errorChip: document.getElementById('error-chip'),
    placeholder: document.getElementById('dashboard-placeholder'),
    dashboard: document.getElementById('dashboard-content'),
    selectedName: document.getElementById('selected-customer-name'),
    tierChip: document.getElementById('tier-chip'),
    kycDetails: document.getElementById('kyc-details'),
    behaviourDetails: document.getElementById('behaviour-details'),
    activityChip: document.getElementById('activity-chip'),
    revenueChart: document.getElementById('revenue-chart'),
    financialDetails: document.getElementById('financial-details'),
    cashflowChart: document.getElementById('cashflow-chart'),
    cashflowDetails: document.getElementById('cashflow-details'),
    creditBand: document.getElementById('credit-band'),
    creditDetails: document.getElementById('credit-details'),
    insightsDetails: document.getElementById('insights-details'),
};

function setStatus(text, type = 'neutral') {
    els.status.textContent = text;
    els.status.classList.remove('good', 'warn');
    if (type === 'good') els.status.classList.add('good');
    if (type === 'warn') els.status.classList.add('warn');
}

function formatCurrency(value, currency = 'SAR') {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(value);
}

function renderCustomers(customers) {
    els.customerList.innerHTML = '';
    if (!customers.length) {
        els.customerList.innerHTML = '<div class="text-muted">No customers found.</div>';
        return;
    }

    customers.forEach((customer) => {
        const card = document.createElement('div');
        card.className = 'customer-card';
        if (customer.id === state.selectedId) card.classList.add('active');

        const credit = customer.latest_credit;
        card.innerHTML = `
            <div class="customer-head">
                <div>
                    <h4>${customer.trade_name || customer.legal_name}</h4>
                    <div class="subtext">${customer.industry || 'Unknown'} • ${customer.city || '—'}</div>
                </div>
                <span class="badge">${customer.subscription_plan || 'standard'}</span>
            </div>
            <div class="metric-row">
                <div class="metric"><div class="label">Credit score</div><div class="value">${credit ? credit.credit_score : 'Pending'}</div></div>
                <div class="metric"><div class="label">Band</div><div class="value">${credit ? credit.credit_band : '—'}</div></div>
                <div class="metric"><div class="label">Limit</div><div class="value">${credit ? formatCurrency(credit.recommended_credit_limit_amount, credit.recommended_credit_limit_currency) : '—'}</div></div>
                <div class="metric"><div class="label">Tenor</div><div class="value">${credit ? `${credit.max_safe_tenor_months} mo` : '—'}</div></div>
            </div>
        `;

        card.addEventListener('click', () => {
            state.selectedId = customer.id;
            els.generate.disabled = false;
            renderCustomers(state.customers);
            els.selectedName.textContent = customer.trade_name || customer.legal_name;
            loadDashboard();
        });

        els.customerList.appendChild(card);
    });
}

async function loadCustomers(showSpinner = true) {
    if (showSpinner) setStatus('Loading customers…');
    try {
        const res = await fetch('/api/customers');
        if (!res.ok) throw new Error('Failed to load customers');
        const data = await res.json();
        state.customers = data;
        renderCustomers(data);
        setStatus(`Loaded ${data.length} customers`, 'good');
    } catch (err) {
        console.error(err);
        setStatus('Unable to load customers', 'warn');
    }
}

function showLoadingDashboard(isLoading) {
    els.loadingChip.hidden = !isLoading;
    els.errorChip.hidden = true;
    els.generate.disabled = isLoading || !state.selectedId;
}

function buildDashboardUrl() {
    const params = new URLSearchParams();
    params.set('viewer_type', els.viewer.value || 'silky_internal');
    if (els.tier.value.trim()) params.set('subscription_tier', els.tier.value.trim());
    if (els.lender.value.trim()) params.set('lender_id', els.lender.value.trim());
    return `/api/credit-dashboard/${state.selectedId}?${params.toString()}`;
}

function renderListItems(items, emptyLabel) {
    if (!items || !items.length) return `<div class="text-muted">${emptyLabel}</div>`;
    return `<ul class="list-inline">${items.map((i) => `<li>${i}</li>`).join('')}</ul>`;
}

function renderKyc(kyc) {
    els.tierChip.textContent = kyc?.relationship_with_silky?.subscription_plan || '—';
    const details = [
        { label: 'Legal name', value: kyc?.legal_name },
        { label: 'Trade name', value: kyc?.trade_name },
        { label: 'Industry', value: kyc?.segment },
        { label: 'City', value: kyc?.registration?.city },
        { label: 'Years in business', value: kyc?.registration?.years_in_business },
        { label: 'Branches', value: kyc?.branches_count },
        { label: 'Modules', value: (kyc?.relationship_with_silky?.modules_enabled || []).join(', ') },
        { label: 'Tenure (months)', value: kyc?.relationship_with_silky?.tenure_months },
    ];
    els.kycDetails.innerHTML = details
        .map((d) => `<div class="detail"><div class="subtext">${d.label}</div><div class="value">${d.value ?? '—'}</div></div>`) // prettier-ignore
        .join('');
}

function renderBehaviour(behaviour) {
    const activity = behaviour?.activity;
    els.activityChip.textContent = activity?.status || '—';

    const featureList = (behaviour?.feature_adoption || [])
        .map((f) => `${f.module} (${f.usage_level})`)
        .join(', ');

    els.behaviourDetails.innerHTML = `
        <div class="detail">
            <div class="subtext">Activity last 90d</div>
            <div class="value">${activity ? `${activity.active_days_last_90} active days, ${activity.logins_last_90} logins` : '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Active users</div>
            <div class="value">${activity ? `${activity.active_users}/${activity.total_users}` : '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Feature adoption</div>
            <div class="value">${featureList || '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Behaviour risks</div>
            <div class="value">${(behaviour?.behaviour_risks || []).join(', ') || 'None'}</div>
        </div>
    `;
}

function buildRevenueSeries(financialHealth) {
    const revenue = financialHealth?.revenue || {};
    const history = revenue.monthly_revenue || revenue.revenue_history || [];

    if (Array.isArray(history) && history.length) {
        return history.map((m, idx) => ({
            label: m.month || `M${idx + 1}`,
            value: m.revenue || m.value || m.amount || 0,
        }));
    }

    const base = revenue.avg_monthly_revenue || 0;
    const growth = revenue.growth_rate_mom || 0.02;
    const points = [];
    let current = base * 0.9;
    for (let i = 0; i < 6; i += 1) {
        current = current * (1 + growth);
        points.push({ label: `M-${6 - i}`, value: Math.max(current, 0) });
    }
    return points;
}

function renderRevenueChart(series) {
    if (!els.revenueChart || typeof Chart === 'undefined') return;
    if (state.charts.revenue) state.charts.revenue.destroy();

    state.charts.revenue = new Chart(els.revenueChart, {
        type: 'line',
        data: {
            labels: series.map((s) => s.label),
            datasets: [
                {
                    label: 'Monthly revenue',
                    data: series.map((s) => s.value),
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56,189,248,0.15)',
                    fill: true,
                    tension: 0.4,
                },
            ],
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.04)' } },
            },
        },
    });
}

function renderFinancials(financialHealth) {
    const revenue = financialHealth?.revenue || {};
    const liquidity = financialHealth?.liquidity || {};
    const concentration = financialHealth?.concentration || {};
    const profitability = financialHealth?.profitability_proxy || {};
    const seasonality = financialHealth?.seasonality || {};

    const series = buildRevenueSeries(financialHealth);
    renderRevenueChart(series);

    els.financialDetails.innerHTML = `
        <div class="detail">
            <div class="subtext">Avg monthly revenue</div>
            <div class="value">${formatCurrency(revenue.avg_monthly_revenue)}</div>
        </div>
        <div class="detail">
            <div class="subtext">Trend</div>
            <div class="value">${revenue.revenue_trend || '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Growth MoM</div>
            <div class="value">${revenue.growth_rate_mom ? `${(revenue.growth_rate_mom * 100).toFixed(1)}%` : '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Liquidity</div>
            <div class="value">DSO ${liquidity.avg_dso_days ?? '—'} | DPO ${liquidity.avg_dpo_days ?? '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Profitability</div>
            <div class="value">${profitability.gross_margin_percent ? `${profitability.gross_margin_percent}% GM` : profitability.comment || '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Concentration</div>
            <div class="value">${concentration.revenue_concentration_comment || '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Seasonality</div>
            <div class="value">${seasonality.seasonality_comment || '—'}</div>
        </div>
    `;
}

function renderCashflow(forecast) {
    if (!forecast) return;
    const base = forecast.base_case || {};
    const conservative = forecast.conservative_case || {};
    const optimistic = forecast.optimistic_case || {};

    const series = [
        { label: 'Base 3m', value: base.net_cash_flow_next_3_months },
        { label: 'Base 12m', value: base.net_cash_flow_next_12_months },
        { label: 'Conservative 3m', value: conservative.net_cash_flow_next_3_months },
        { label: 'Optimistic 3m', value: optimistic.net_cash_flow_next_3_months },
    ];

    if (state.charts.cashflow) state.charts.cashflow.destroy();
    if (els.cashflowChart && typeof Chart !== 'undefined') {
        state.charts.cashflow = new Chart(els.cashflowChart, {
            type: 'bar',
            data: {
                labels: series.map((s) => s.label),
                datasets: [
                    {
                        label: 'Cashflow',
                        data: series.map((s) => s.value),
                        backgroundColor: ['#38bdf8', '#0ea5e9', '#94a3b8', '#a78bfa'],
                    },
                ],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#cbd5e1' }, grid: { display: false } },
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                },
            },
        });
    }

    els.cashflowDetails.innerHTML = `
        <div class="detail">
            <div class="subtext">Base case</div>
            <div class="value">${formatCurrency(base.net_cash_flow_next_3_months)} (3m) • ${formatCurrency(base.net_cash_flow_next_12_months)} (12m)</div>
        </div>
        <div class="detail">
            <div class="subtext">Conservative</div>
            <div class="value">${formatCurrency(conservative.net_cash_flow_next_3_months)} (3m)</div>
        </div>
        <div class="detail">
            <div class="subtext">Optimistic</div>
            <div class="value">${formatCurrency(optimistic.net_cash_flow_next_3_months)} (3m)</div>
        </div>
        <div class="detail">
            <div class="subtext">Drivers</div>
            <div class="value">${(forecast.key_drivers || []).join(', ') || '—'}</div>
        </div>
    `;
}

function renderCredit(credit) {
    els.creditBand.textContent = credit?.credit_band || '—';
    const limit = credit?.recommended_credit_limit;
    const explanation = credit?.score_explanation || {};

    els.creditDetails.innerHTML = `
        <div class="detail">
            <div class="subtext">Credit score</div>
            <div class="value">${credit?.credit_score ?? '—'} / 100</div>
        </div>
        <div class="detail">
            <div class="subtext">Recommended limit</div>
            <div class="value">${limit ? formatCurrency(limit.amount, limit.currency) : '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Max tenor</div>
            <div class="value">${credit?.max_safe_tenor_months ? `${credit.max_safe_tenor_months} months` : '—'}</div>
        </div>
        <div class="detail">
            <div class="subtext">Drivers</div>
            <div class="value">${renderListItems(explanation.positive_drivers, 'No positive drivers')}</div>
        </div>
        <div class="detail">
            <div class="subtext">Risks</div>
            <div class="value">${renderListItems(explanation.risk_factors, 'No risk factors')}</div>
        </div>
    `;
}

function renderInsights(data) {
    const offers = data.available_offers || [];
    const flags = data.early_warning_flags || [];
    const lenderRecs = data.recommendations_for_lender || [];
    const merchantActions = data.improvement_actions_for_merchant || [];

    els.insightsDetails.innerHTML = `
        <div class="insight-block">
            <div class="subtext">Available offers</div>
            ${renderListItems(offers.map((o) => `${o.product_type}: ${formatCurrency(o.amount, o.currency)}`), 'No offers yet')}
        </div>
        <div class="insight-block">
            <div class="subtext">Early warning flags</div>
            ${renderListItems(flags, 'No flags detected')}
        </div>
        <div class="insight-block">
            <div class="subtext">Recommendations for lender</div>
            ${renderListItems(lenderRecs, 'No lender notes')}
        </div>
        <div class="insight-block">
            <div class="subtext">Improvement actions</div>
            ${renderListItems(merchantActions, 'No actions logged')}
        </div>
    `;
}

function renderDashboard(data) {
    state.dashboard = data;
    els.placeholder.hidden = true;
    els.dashboard.hidden = false;

    renderKyc(data.kyc_profile);
    renderBehaviour(data.behaviour_profile);
    renderFinancials(data.financial_health);
    renderCashflow(data.cashflow_forecast);
    renderCredit(data.credit_analysis);
    renderInsights(data);
}

async function loadDashboard() {
    if (!state.selectedId) return;
    showLoadingDashboard(true);
    try {
        const res = await fetch(buildDashboardUrl());
        if (!res.ok) throw new Error('Failed to load dashboard');
        const data = await res.json();
        renderDashboard(data);
        setStatus(`Dashboard ready for customer ${state.selectedId}`, 'good');
        showLoadingDashboard(false);
        loadCustomers(false);
    } catch (err) {
        console.error(err);
        els.errorChip.hidden = false;
        showLoadingDashboard(false);
        setStatus('Dashboard generation failed', 'warn');
    }
}

function init() {
    els.refresh.addEventListener('click', () => loadCustomers());
    els.generate.addEventListener('click', loadDashboard);
    els.viewer.addEventListener('change', () => state.selectedId && loadDashboard());
    els.tier.addEventListener('change', () => state.selectedId && loadDashboard());
    els.lender.addEventListener('change', () => state.selectedId && loadDashboard());
    loadCustomers();
}

init();
