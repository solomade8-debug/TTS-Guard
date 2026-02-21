"""
TTS Guard — Financials Page
Revenue tracking, payment status, collection rate, client breakdown,
payment history, and outstanding invoices.
"""

import streamlit as st
import pandas as pd
from database import (
    get_financial_summary,
    get_client_financial_breakdown,
    get_payment_history,
    get_monthly_revenue,
    get_outstanding_invoices,
)

st.markdown(
    '<h1 class="fire-header">💰 Financial Overview</h1>',
    unsafe_allow_html=True,
)
st.caption("Revenue tracking and payment status for all AMC contracts")

# ---------------------------------------------------------------------------
# TOP ROW — 4 Financial Metrics
# ---------------------------------------------------------------------------
financials = get_financial_summary()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "Total Contract Value",
        f"AED {financials['total_contract_value']:,.0f}",
        help="Sum of all active contract annual values",
    )
with col2:
    st.metric(
        "Collected",
        f"AED {financials['total_collected']:,.0f}",
        delta=f"{financials['collection_pct']:.0f}%",
    )
with col3:
    st.metric(
        "Outstanding",
        f"AED {financials['total_outstanding']:,.0f}",
        delta=f"{financials['outstanding_count']} invoices",
        delta_color="inverse",
    )
with col4:
    st.metric(
        "Overdue Payments",
        f"AED {financials['total_overdue']:,.0f}",
        delta=f"{financials['overdue_count']} overdue",
        delta_color="inverse",
    )

# ---------------------------------------------------------------------------
# COLLECTION RATE PROGRESS BAR
# ---------------------------------------------------------------------------
collection_pct = financials["collection_pct"]
st.progress(
    min(collection_pct / 100, 1.0),
    text=f"Collection Rate: {collection_pct:.1f}%",
)

st.divider()

# ---------------------------------------------------------------------------
# CLIENT FINANCIAL SUMMARY TABLE
# ---------------------------------------------------------------------------
st.subheader("📊 Client Financial Summary")

client_fin = get_client_financial_breakdown()
if len(client_fin) > 0:
    # Format currency columns
    for col_name in ["Contract Value (AED)", "Paid (AED)", "Outstanding (AED)"]:
        client_fin[col_name] = client_fin[col_name].apply(lambda x: f"AED {x:,.0f}")

    # Color-code status
    def style_status(status):
        if status == "Fully Paid":
            return f"🟢 {status}"
        elif status == "Payment Overdue":
            return f"🔴 {status}"
        else:
            return f"🟡 {status}"

    client_fin["Status"] = client_fin["Status"].apply(style_status)

    st.dataframe(client_fin, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# MONTHLY COLLECTIONS CHART
# ---------------------------------------------------------------------------
st.subheader("📈 Monthly Collections")

monthly_rev = get_monthly_revenue(6)
if len(monthly_rev) > 0:
    chart_data = monthly_rev.set_index("month")
    chart_data.columns = ["Amount (AED)"]
    st.bar_chart(chart_data, color="#ff6600")
else:
    st.info("No payment data available for chart.")

st.divider()

# ---------------------------------------------------------------------------
# RECENT PAYMENTS TABLE
# ---------------------------------------------------------------------------
st.subheader("💳 Recent Payments")

payments_df = get_payment_history(20)
if len(payments_df) > 0:
    # Format amount
    payments_df["Amount (AED)"] = payments_df["Amount (AED)"].apply(
        lambda x: f"AED {x:,.0f}"
    )
    # Style status
    payments_df["Status"] = payments_df["Status"].apply(
        lambda s: {
            "received": "✅ Received",
            "pending": "🟡 Pending",
            "overdue": "🔴 Overdue",
            "partial": "🟠 Partial",
        }.get(s, s)
    )
    # Format method
    payments_df["Method"] = payments_df["Method"].apply(
        lambda m: m.replace("_", " ").title() if m else "—"
    )
    st.dataframe(payments_df, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# OUTSTANDING INVOICES
# ---------------------------------------------------------------------------
with st.expander("📋 View Outstanding Invoices"):
    outstanding_df = get_outstanding_invoices()
    if len(outstanding_df) > 0:
        # Format
        outstanding_df["Contract Value (AED)"] = outstanding_df["Contract Value (AED)"].apply(
            lambda x: f"AED {x:,.0f}"
        )
        outstanding_df["Amount Due (AED)"] = outstanding_df["Amount Due (AED)"].apply(
            lambda x: f"AED {x:,.0f}"
        )
        outstanding_df["Status"] = outstanding_df["Status"].apply(
            lambda s: {
                "pending": "🟡 Pending",
                "overdue": "🔴 Overdue",
            }.get(s, s)
        )
        st.dataframe(outstanding_df, use_container_width=True, hide_index=True)
    else:
        st.success("No outstanding invoices!")
