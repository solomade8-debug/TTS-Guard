"""
TTS Guard — Reports Page
Monthly compliance reports with charts (6 months depth).
"""

import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_inspections_by_month,
    get_complaints_by_month,
    get_all_clients,
)

st.markdown(
    '<h1 class="fire-header">📈 Reports</h1>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# MONTH SELECTOR (last 6 months)
# ---------------------------------------------------------------------------
today = date.today()
month_options = []
for i in range(6):
    m = today.month - i
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    month_options.append((y, m, date(y, m, 1).strftime("%B %Y")))

selected_month = st.selectbox(
    "Select Month",
    options=month_options,
    format_func=lambda x: x[2],
)

year, month, label = selected_month

st.divider()

# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------
inspections_df = get_inspections_by_month(year, month)
complaints_df = get_complaints_by_month(year, month)

# ---------------------------------------------------------------------------
# SUMMARY METRICS
# ---------------------------------------------------------------------------
st.subheader(f"📊 Summary — {label}")

total_inspections = len(inspections_df)
total_equipment = int(inspections_df["items_checked"].sum()) if total_inspections > 0 else 0
total_passed = int(inspections_df["items_passed"].sum()) if total_inspections > 0 else 0
compliance_rate = (total_passed / total_equipment * 100) if total_equipment > 0 else 0

total_complaints = len(complaints_df)
resolved_complaints = len(complaints_df[complaints_df["status"] == "resolved"]) if total_complaints > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Inspections Completed", total_inspections)
with col2:
    st.metric("Equipment Checked", f"{total_equipment:,}")
with col3:
    st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
with col4:
    st.metric(
        "Complaints",
        f"{resolved_complaints}/{total_complaints} resolved",
    )

st.divider()

# ---------------------------------------------------------------------------
# CHARTS
# ---------------------------------------------------------------------------
chart_left, chart_right = st.columns(2)

with chart_left:
    st.subheader("Inspections by Client")
    if total_inspections > 0:
        by_client = (
            inspections_df.groupby("client_name")
            .size()
            .reset_index(name="Inspections")
        )
        by_client = by_client.set_index("client_name")
        st.bar_chart(by_client, color="#012f5d")
    else:
        st.info(f"No inspections recorded for {label}.")

with chart_right:
    st.subheader("Complaints by Priority")
    if total_complaints > 0:
        by_priority = (
            complaints_df.groupby("priority")
            .size()
            .reset_index(name="Count")
        )
        # Order priorities
        priority_order = {"high": 0, "medium": 1, "low": 2}
        by_priority["order"] = by_priority["priority"].map(priority_order)
        by_priority = by_priority.sort_values("order").drop(columns=["order"])
        by_priority = by_priority.set_index("priority")
        st.bar_chart(by_priority, color="#ff6600")
    else:
        st.info(f"No complaints recorded for {label}.")

st.divider()

# ---------------------------------------------------------------------------
# INSPECTION DETAIL TABLE
# ---------------------------------------------------------------------------
st.subheader("Inspection Details")
if total_inspections > 0:
    detail_df = inspections_df[
        ["inspection_date", "client_name", "building_name", "technician",
         "items_checked", "items_passed", "items_failed"]
    ].copy()
    detail_df.columns = [
        "Date", "Client", "Building", "Technician",
        "Checked", "Passed", "Failed",
    ]
    st.dataframe(detail_df, use_container_width=True, hide_index=True)
else:
    st.info(f"No inspection data for {label}.")
