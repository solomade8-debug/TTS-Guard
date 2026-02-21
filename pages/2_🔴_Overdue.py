"""
TTS Guard — Overdue Inspections Page
Lists overdue buildings with scheduling capability (date + technician).
"""

import streamlit as st
from datetime import date, timedelta
from database import (
    get_overdue_inspections,
    schedule_inspection,
    is_building_scheduled,
    TECHNICIANS,
)

st.markdown(
    '<h1 class="fire-header">🔴 Overdue Inspections</h1>',
    unsafe_allow_html=True,
)

overdue_df = get_overdue_inspections()
overdue_count = len(overdue_df)

if overdue_count == 0:
    st.success("✅ No overdue inspections! All buildings are up to date.")
    st.stop()

st.markdown(
    f'<p style="font-size: 1.1rem; color: #e60000; font-weight: 600;">'
    f"⚠️ {overdue_count} building{'s' if overdue_count > 1 else ''} "
    f"with overdue inspections</p>",
    unsafe_allow_html=True,
)

st.divider()

for idx, row in overdue_df.iterrows():
    building_id = row["building_id"]

    # Check if already scheduled
    if is_building_scheduled(building_id):
        continue

    with st.container(border=True):
        top_left, top_right = st.columns([3, 1])

        with top_left:
            st.markdown(f"### {row['building_name']}")
            st.markdown(
                f"**{row['client_name']}** · {row['area']}"
            )
            st.caption(
                f"📦 {row['equipment_count']} equipment items · "
                f"💰 AED {row['annual_value']:,.0f}/year"
            )

        with top_right:
            days_overdue = max(
                int(row["days_since_last"]) - int(365 / row["visits_per_year"]),
                0,
            )
            st.metric(
                "Days Overdue",
                days_overdue,
                delta=f"-{days_overdue} days",
                delta_color="inverse",
            )

        # Last inspection info
        if row["last_inspection_date"]:
            st.caption(f"Last inspection: {row['last_inspection_date']}")
        else:
            st.caption("⚠️ No previous inspection on record")

        # Schedule section
        schedule_key = f"schedule_{building_id}"
        if schedule_key not in st.session_state:
            st.session_state[schedule_key] = False

        if not st.session_state[schedule_key]:
            if st.button(
                "📅 Mark as Scheduled",
                key=f"btn_schedule_{building_id}",
                use_container_width=True,
            ):
                st.session_state[schedule_key] = True
                st.rerun()
        else:
            st.markdown("---")
            st.markdown("**Schedule Inspection**")
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                sched_date = st.date_input(
                    "Inspection Date",
                    value=date.today() + timedelta(days=2),
                    min_value=date.today(),
                    key=f"date_{building_id}",
                )
            with s_col2:
                sched_tech = st.selectbox(
                    "Assign Technician",
                    TECHNICIANS,
                    key=f"tech_{building_id}",
                )

            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "✅ Confirm Schedule",
                    key=f"confirm_{building_id}",
                    use_container_width=True,
                ):
                    schedule_inspection(
                        building_id,
                        sched_date.isoformat(),
                        sched_tech,
                    )
                    st.session_state[schedule_key] = False
                    st.success(
                        f"✅ {row['building_name']} scheduled for "
                        f"{sched_date.strftime('%B %d, %Y')} — "
                        f"Assigned to {sched_tech}"
                    )
                    st.rerun()
            with c2:
                if st.button(
                    "❌ Cancel",
                    key=f"cancel_{building_id}",
                    use_container_width=True,
                ):
                    st.session_state[schedule_key] = False
                    st.rerun()
