"""
TTS Guard — Main Entry Point
Welcome page with branding, key stats, guided tour, and sidebar configuration.
"""

import streamlit as st
import os
from datetime import date
from database import init_db, reset_db, has_data, get_active_contracts_count, get_all_clients, get_all_buildings, get_financial_summary
from seed_data import seed

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="TTS Guard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# THEME TOGGLE (persisted in session state)
# ---------------------------------------------------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # default to dark

dark = st.session_state.dark_mode

# ---------------------------------------------------------------------------
# TTS BRAND CSS THEME — DARK / LIGHT
# ---------------------------------------------------------------------------
# Color tokens
if dark:
    BG = "#0e1117"; BG2 = "#1a1f2e"; SIDEBAR_BG = "#131720"
    BORDER = "#2a2f3a"; TEXT = "#e0e0e0"; TEXT_MUTED = "#9ca3af"
    CARD_BG = "#1a1f2e"; METRIC_VAL = "#ff6600"; METRIC_ACCENT = "#ff6600"
    HEADER_HEAD = "#ff6600"; HEADER_TAIL = "#ff8c3a"
    SHADOW = "rgba(0,0,0,0.3)"; HOVER_SHADOW = "rgba(255,102,0,0.15)"
    BTN_HOVER_TEXT = "#0e1117"; DIVIDER = "#2a2f3a"
    STATUS_RED = "#ff4444"; STATUS_GREEN = "#34d399"
    TOPBAR = "linear-gradient(90deg, #0a1628, #012f5d 60%, #ff6600)"
else:
    BG = "#ffffff"; BG2 = "#f8f8fa"; SIDEBAR_BG = "#f8f8fa"
    BORDER = "#e5e5e5"; TEXT = "#222222"; TEXT_MUTED = "#777777"
    CARD_BG = "#ffffff"; METRIC_VAL = "#012f5d"; METRIC_ACCENT = "#012f5d"
    HEADER_HEAD = "#012f5d"; HEADER_TAIL = "#ff6600"
    SHADOW = "rgba(0,0,0,0.05)"; HOVER_SHADOW = "rgba(1,47,93,0.12)"
    BTN_HOVER_TEXT = "#ffffff"; DIVIDER = "#e5e5e5"
    STATUS_RED = "#e60000"; STATUS_GREEN = "#00C853"
    TOPBAR = "linear-gradient(90deg, #012f5d, #012f5d 70%, #ff6600)"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Open+Sans:wght@400;600&display=swap');

    /* Global typography */
    html, body, [class*="css"] {{
        font-family: 'Open Sans', sans-serif;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Roboto', sans-serif !important;
    }}

    /* Main app background */
    .stApp {{
        background-color: {BG} !important;
    }}

    /* Top header bar */
    .stApp > header {{
        background: {TOPBAR} !important;
    }}

    /* Metric card styling */
    [data-testid="stMetricValue"] {{
        font-size: 1.8rem;
        font-weight: 700;
        font-family: 'Roboto', sans-serif !important;
        color: {METRIC_VAL} !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT_MUTED} !important;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid {BORDER};
    }}

    /* Dataframe styling */
    .stDataFrame {{
        border-radius: 8px;
    }}

    /* Metric card borders */
    div[data-testid="stMetric"] {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-left: 4px solid {METRIC_ACCENT};
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0px 2px 10px {SHADOW};
    }}

    /* Section headers */
    .fire-header {{
        background: linear-gradient(90deg, {HEADER_HEAD}, {HEADER_TAIL});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-family: 'Roboto', sans-serif !important;
    }}

    /* Status colors */
    .status-overdue {{ color: {STATUS_RED}; font-weight: 600; }}
    .status-due-soon {{ color: #ff6600; font-weight: 600; }}
    .status-ok {{ color: {STATUS_GREEN}; font-weight: 600; }}

    /* Hero stat cards */
    .hero-stat {{
        text-align: center;
        padding: 20px;
        background: {CARD_BG};
        border-radius: 10px;
        border: 1px solid {BORDER};
        box-shadow: 0px 4px 15px {SHADOW};
        transition: all 0.3s ease;
    }}
    .hero-stat:hover {{
        box-shadow: 0px 4px 20px {HOVER_SHADOW};
        border-color: #ff6600;
    }}
    .hero-stat h2 {{
        color: {METRIC_VAL};
        margin: 0;
        font-size: 2.2rem;
        font-family: 'Roboto', sans-serif !important;
    }}
    .hero-stat p {{
        color: {TEXT_MUTED};
        margin: 4px 0 0 0;
        font-size: 0.9rem;
    }}

    /* Navigation cards */
    .nav-card {{
        padding: 18px;
        background: {CARD_BG};
        border-radius: 10px;
        border: 1px solid {BORDER};
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0px 2px 10px {SHADOW};
    }}
    .nav-card:hover {{
        border-color: #ff6600;
        box-shadow: 0 4px 15px {HOVER_SHADOW};
        transform: translateY(-2px);
    }}
    .nav-card h3 {{
        margin: 8px 0 4px 0;
        font-size: 1rem;
        color: {TEXT};
        font-family: 'Roboto', sans-serif !important;
    }}
    .nav-card p {{
        color: {TEXT_MUTED};
        font-size: 0.8rem;
        margin: 0;
    }}

    /* Buttons — TTS orange */
    .stButton > button {{
        border-color: #ff6600;
        color: #ff6600;
        transition: all 0.3s ease;
    }}
    .stButton > button:hover {{
        background-color: #ff6600;
        color: {BTN_HOVER_TEXT};
        border-color: #ff6600;
    }}

    /* Progress bar */
    .stProgress > div > div > div {{
        background-color: #ff6600 !important;
    }}

    /* Expander headers */
    .streamlit-expanderHeader {{
        font-family: 'Roboto', sans-serif !important;
        color: {TEXT} !important;
    }}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        color: #ff6600 !important;
        border-bottom-color: #ff6600 !important;
    }}

    /* Dividers */
    hr {{
        border-color: {DIVIDER} !important;
    }}

    /* Alert banners */
    .stAlert [data-testid="stNotificationContentWarning"] {{
        border-left-color: #ff6600 !important;
    }}
    .stAlert [data-testid="stNotificationContentError"] {{
        border-left-color: {STATUS_RED} !important;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# DATABASE INIT
# ---------------------------------------------------------------------------
init_db()
if not has_data():
    seed()

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

with st.sidebar:
    # Theme toggle
    theme_col1, theme_col2 = st.columns([3, 1])
    with theme_col1:
        st.markdown(
            f'<p style="color: {TEXT_MUTED}; font-size: 0.8rem; margin: 4px 0;">Theme</p>',
            unsafe_allow_html=True,
        )
    with theme_col2:
        if st.button("🌙" if not dark else "☀️", key="theme_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    # Logo
    logo_bg = "#012f5d" if dark else "#012f5d"
    if os.path.exists(LOGO_PATH):
        import base64
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div style="background-color: {logo_bg}; padding: 16px 20px; '
            f'border-radius: 10px; text-align: center; margin-bottom: 8px;">'
            f'<img src="data:image/png;base64,{logo_b64}" width="180" />'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<h2 style="color: {METRIC_VAL}; font-family: Roboto, sans-serif; '
            f'font-weight: 700; margin: 0;">TTS Guard</h2>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<p style="color: {TEXT_MUTED}; font-size: 0.85rem; margin-top: 2px;">'
        "Talent Technical Services</p>",
        unsafe_allow_html=True,
    )
    st.markdown(f"📅 {date.today().strftime('%B %d, %Y')}")
    st.markdown("📍 Abu Dhabi, UAE")

    st.divider()

    # Demo notes expander
    with st.expander("📋 Demo Notes"):
        st.markdown("""
        **Presenter's Guide:**
        - **Dashboard**: Show 4 inspection metrics + financial health + alert banner
        - **Overdue**: Demonstrate scheduling an overdue inspection
        - **Inspect**: Submit an inspection, download PDF, create complaint ticket
        - **Clients**: Expand a client to show buildings + financials
        - **Reports**: Switch months to show trend data
        - **Financials**: Highlight collection rate and outstanding invoices
        """)

    st.divider()

    # Two-step reset
    if "reset_confirm" not in st.session_state:
        st.session_state.reset_confirm = False

    if not st.session_state.reset_confirm:
        if st.button("🔄 Reset Demo Data", use_container_width=True):
            st.session_state.reset_confirm = True
            st.rerun()
    else:
        st.warning("⚠️ This will erase all data including submitted inspections.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm", use_container_width=True):
                reset_db()
                seed()
                st.session_state.reset_confirm = False
                st.success("Demo data reset!")
                st.rerun()
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.reset_confirm = False
                st.rerun()

# ---------------------------------------------------------------------------
# WELCOME PAGE
# ---------------------------------------------------------------------------
st.markdown(
    f'<h1 style="background: linear-gradient(90deg, {HEADER_HEAD}, {HEADER_TAIL}); '
    "-webkit-background-clip: text; -webkit-text-fill-color: transparent; "
    'font-family: Roboto, sans-serif; font-weight: 700; '
    'margin-bottom: 0;">TTS Guard</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<h3 style="color: {METRIC_VAL}; font-family: Roboto, sans-serif; '
    f'font-weight: 500; margin-top: 0;">AMC Management Dashboard</h3>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="color: {TEXT_MUTED}; font-size: 1.05rem; margin-top: -8px;">'
    "Centralized inspection tracking, compliance monitoring, and financial oversight "
    "for fire safety AMC contracts across Abu Dhabi.</p>",
    unsafe_allow_html=True,
)

st.divider()

# Key stats
clients_df = get_all_clients()
buildings_df = get_all_buildings()
contracts_count = get_active_contracts_count()
financials = get_financial_summary()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        f'<div class="hero-stat"><h2>{len(clients_df)}</h2><p>Active Clients</p></div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f'<div class="hero-stat"><h2>{len(buildings_df)}</h2><p>Buildings Managed</p></div>',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f'<div class="hero-stat"><h2>{contracts_count}</h2><p>Active Contracts</p></div>',
        unsafe_allow_html=True,
    )
with col4:
    total_val = financials["total_contract_value"]
    st.markdown(
        f'<div class="hero-stat"><h2>AED {total_val:,.0f}</h2><p>Annual Contract Value</p></div>',
        unsafe_allow_html=True,
    )

st.divider()

# Guided Tour
if "show_tour" not in st.session_state:
    st.session_state.show_tour = False

if st.button("🎯 Take a Tour", use_container_width=False):
    st.session_state.show_tour = not st.session_state.show_tour

if st.session_state.show_tour:
    st.info("""
    **Welcome to TTS Guard! Here's what each section does:**

    1. **📊 Dashboard** — Your command center. See overdue alerts, upcoming inspections, recent complaints, financial health, and client overview all in one place.

    2. **🔴 Overdue** — Buildings that need immediate attention. Schedule inspections with a date and technician right from here.

    3. **📋 Inspect** — Submit inspection results. Check equipment, add notes, download a professional PDF report, and auto-create complaint tickets for failed items.

    4. **👥 Clients** — Complete directory of all clients and their buildings with contact info, equipment counts, and financial summaries.

    5. **📈 Reports** — Monthly compliance reports with charts showing inspections per client and complaint breakdowns.

    6. **💰 Financials** — Revenue dashboard showing collection rates, outstanding payments, client-wise breakdowns, and payment history.

    *Use the sidebar navigation to explore each section. Click "Take a Tour" again to hide this guide.*
    """)

st.divider()

# Navigation cards
st.markdown("### Quick Navigation")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        '<div class="nav-card"><h3>📊 Dashboard</h3>'
        "<p>Metrics, alerts & overview</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="nav-card"><h3>🔴 Overdue</h3>'
        "<p>Schedule overdue inspections</p></div>",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        '<div class="nav-card"><h3>📋 Inspect</h3>'
        "<p>Submit inspections & PDF reports</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="nav-card"><h3>👥 Clients</h3>'
        "<p>Client & building directory</p></div>",
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        '<div class="nav-card"><h3>📈 Reports</h3>'
        "<p>Monthly compliance summaries</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="nav-card"><h3>💰 Financials</h3>'
        "<p>Revenue & payment tracking</p></div>",
        unsafe_allow_html=True,
    )
