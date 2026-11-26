"""PoultryGuard AI — Farm Intelligence MVP."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import altair as alt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import initialise_database  # noqa: E402
from app.frontend.ui_components import (  # noqa: E402
    CHART_COLORS,
    apply_design_system,
    form_columns,
    loading_indicator,
    render_app_header,
    render_data_table,
    render_empty_state,
    render_feedback,
    render_kpi_card,
    render_page_header,
    render_section_header,
    render_sidebar_brand,
    render_sidebar_navigation,
    render_status_label,
)
from app.services.analytics_service import AnalyticsService  # noqa: E402
from app.services.farm_service import DuplicateRecordError, FarmService  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PoultryGuard AI",
    page_icon="🐔",
    layout="wide",
)

apply_design_system()

# ---------------------------------------------------------------------------
# Initialise database on first run
# ---------------------------------------------------------------------------

initialise_database()

# ---------------------------------------------------------------------------
# Cached service instances
# ---------------------------------------------------------------------------


@st.cache_resource
def get_farm_service() -> FarmService:
    return FarmService()


@st.cache_resource
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


@st.cache_resource
def get_retriever():
    from rag.retrieval import KnowledgeBaseRetriever

    return KnowledgeBaseRetriever(
        index_path=PROJECT_ROOT / "vector_store" / "poultryguard.faiss",
        metadata_path=PROJECT_ROOT / "vector_store" / "metadata.json",
    )


@st.cache_resource
def get_answer_generator():
    from app.services.answer_generator import PoultryAnswerGenerator

    return PoultryAnswerGenerator()


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults: dict[str, Any] = {
        "selected_farm_id": None,
        "selected_flock_id": None,
        "nav_section": "Knowledge Assistant",
        "nav_farm_tab": "Dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_state()


def _selector_options(
    items: list[dict[str, Any]], primary_key: str, detail_key: str
) -> dict[str, int]:
    """Build readable selector labels without collapsing duplicate names."""
    counts: dict[str, int] = {}
    for item in items:
        primary = str(item.get(primary_key) or "Unnamed")
        counts[primary] = counts.get(primary, 0) + 1

    options: dict[str, int] = {}
    for item in items:
        primary = str(item.get(primary_key) or "Unnamed")
        detail = str(item.get(detail_key) or "").strip()
        label = f"{primary} · {detail}" if counts[primary] > 1 and detail else primary
        if label in options:
            label = f"{label} · #{item['id']}"
        options[label] = item["id"]
    return options


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

active_farm_name = None
with st.sidebar:
    render_sidebar_brand()
    st.divider()

    section = render_sidebar_navigation(
        ["Knowledge Assistant", "Farm Intelligence"], key="nav_section"
    )

    if section == "Farm Intelligence":
        st.divider()
        farms = get_farm_service().list_farms()
        if farms:
            farm_options = _selector_options(farms, "farm_name", "location")
            selected_name = st.selectbox(
                "Active farm context",
                list(farm_options.keys()),
                key="_sidebar_farm_select",
            )
            st.session_state.selected_farm_id = farm_options[selected_name]
            active_farm_name = next(
                (
                    farm["farm_name"]
                    for farm in farms
                    if farm["id"] == st.session_state.selected_farm_id
                ),
                None,
            )

            flocks = get_farm_service().list_flocks(st.session_state.selected_farm_id)
            if flocks:
                flock_options = _selector_options(flocks, "flock_name", "species")
                selected_flock = st.selectbox(
                    "Active flock context",
                    list(flock_options.keys()),
                    key="_sidebar_flock_select",
                )
                st.session_state.selected_flock_id = flock_options[selected_flock]
            else:
                st.session_state.selected_flock_id = None
                st.caption("No flocks registered for this farm.")
        else:
            st.session_state.selected_farm_id = None
            st.session_state.selected_flock_id = None
            st.caption("No farms registered yet.")

render_app_header(
    section,
    active_farm_name if section == "Farm Intelligence" else None,
)

# ---------------------------------------------------------------------------
# SECTION: Knowledge Assistant
# ---------------------------------------------------------------------------

if section == "Knowledge Assistant":
    render_page_header(
        "Knowledge Assistant",
        "Evidence-informed poultry guidance from the curated knowledge base.",
    )
    st.info(
        "Answers are generated from retrieved knowledge-base passages. "
        "They may be incomplete or incorrect and do not replace advice "
        "from a qualified poultry veterinarian."
    )

    with st.sidebar:
        st.divider()
        top_k = st.slider(
            "Evidence passages",
            min_value=1,
            max_value=10,
            value=5,
            help="Number of knowledge-base passages to retrieve.",
        )

    with st.form("poultry_question_form"):
        question = st.text_area(
            "What would you like to know?",
            placeholder=(
                "Example: How should a poultry house be cleaned "
                "and disinfected between flocks?"
            ),
            height=110,
        )
        submitted = st.form_submit_button(
            "Ask PoultryGuard AI", type="primary", use_container_width=True
        )

    if submitted:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                with loading_indicator("Finding relevant evidence..."):
                    passages = get_retriever().search(question.strip(), top_k=top_k)

                if not passages:
                    st.warning(
                        "No relevant passages were found. Try rephrasing "
                        "your question or consult a poultry professional."
                    )
                else:
                    with loading_indicator("Generating an evidence-based answer..."):
                        result = get_answer_generator().generate(
                            question=question.strip(), passages=passages
                        )

                    render_section_header("Answer")
                    st.markdown(result.answer)
                    render_section_header("Supporting sources")

                    for number, source in enumerate(result.sources, start=1):
                        source_path = str(source.get("source", "Unknown source"))
                        section_name = str(source.get("section", "Unspecified section"))
                        score = source.get("score")
                        heading = f"{number}. {section_name}"
                        if score is not None:
                            heading += f" — similarity {float(score):.3f}"
                        with st.expander(heading):
                            st.markdown(f"**Source file:** `{source_path}`")
                            st.caption(
                                "Similarity indicates retrieval relevance, "
                                "not factual accuracy."
                            )

            except ValueError as exc:
                render_feedback("error", str(exc))
            except Exception as exc:
                render_feedback(
                    "error",
                    "PoultryGuard could not complete the request. "
                    "Check your API access and terminal output, then try again.",
                )
                st.caption(f"{type(exc).__name__}: {exc}")

    st.divider()
    st.markdown(
        (
            '<div class="pg-footer">'
            "Local knowledge retrieval · Groq answer generation"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# SECTION: Farm Intelligence
# ---------------------------------------------------------------------------

else:
    render_page_header(
        "Farm Intelligence",
        "Manage farm records and understand flock performance.",
    )

    tab_dashboard, tab_farms, tab_flocks, tab_records, tab_analytics = st.tabs(
        ["Dashboard", "Farm Profiles", "Flock Management", "Daily Records", "Analytics"]
    )

    # -----------------------------------------------------------------------
    # TAB: Dashboard
    # -----------------------------------------------------------------------

    with tab_dashboard:
        render_section_header(
            "Farm Dashboard", "A current overview of your farm and flocks."
        )

        farms = get_farm_service().list_farms()
        if not farms:
            render_empty_state(
                "No farms registered yet",
                "Open Farm Profiles to register your first farm.",
            )
        else:
            farm_id = st.session_state.selected_farm_id
            if farm_id is None:
                st.info("Select a farm from the sidebar to view its dashboard.")
            else:
                farm = get_farm_service().get_farm(farm_id)
                if farm:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Farm:** {farm['farm_name']}")
                        st.markdown(f"**Farmer:** {farm['farmer_name']}")
                        st.markdown(f"**Location:** {farm.get('location') or '—'}")
                    with col2:
                        st.markdown(
                            f"**Production type:** {farm.get('production_type') or '—'}"
                        )
                        st.markdown(f"**Phone:** {farm.get('phone') or '—'}")
                        st.markdown(f"**Email:** {farm.get('email') or '—'}")

                st.divider()
                flocks = get_farm_service().list_flocks(farm_id)
                if not flocks:
                    render_empty_state(
                        "No flocks registered",
                        "Open Flock Management to add a flock to this farm.",
                    )
                else:
                    st.markdown(f"**{len(flocks)} flock(s) registered**")
                    analytics = get_analytics_service()
                    cols = st.columns(min(len(flocks), 3))
                    for idx, flock in enumerate(flocks):
                        with cols[idx % 3]:
                            try:
                                summary = analytics.get_flock_summary(flock["id"])
                                render_kpi_card(
                                    flock["flock_name"],
                                    f"{int(summary['current_flock_size']):,} birds",
                                    f"{summary['record_count']} records · "
                                    f"{summary['mortality_rate_percent']}% mortality",
                                )
                            except Exception:
                                render_kpi_card(flock["flock_name"], "Unavailable")

    # -----------------------------------------------------------------------
    # TAB: Farm Profiles
    # -----------------------------------------------------------------------

    with tab_farms:
        render_section_header("Farm Profiles", "Register and review farm details.")

        with st.expander("➕ Register a new farm", expanded=False):
            with st.form("register_farm_form", clear_on_submit=True):
                col1, col2 = form_columns(2)
                with col1:
                    new_farm_name = st.text_input("Farm name *")
                    new_farmer_name = st.text_input("Farmer name *")
                    new_location = st.text_input("Location *")
                with col2:
                    new_production_type = st.selectbox(
                        "Production type",
                        ["", "Broiler", "Layer", "Breeder", "Dual Purpose", "Other"],
                    )
                    new_phone = st.text_input("Phone number")
                    new_email = st.text_input("Email address")

                if st.form_submit_button("Register farm", type="primary"):
                    try:
                        farm_id = get_farm_service().create_farm(
                            farm_name=new_farm_name,
                            farmer_name=new_farmer_name,
                            location=new_location,
                            production_type=new_production_type,
                            phone=new_phone or None,
                            email=new_email or None,
                        )
                        render_feedback(
                            "success", f"Farm registered successfully (ID: {farm_id})."
                        )
                        st.cache_resource.clear()
                        st.rerun()
                    except ValueError as exc:
                        render_feedback("error", str(exc))

        farms = get_farm_service().list_farms()
        if not farms:
            render_empty_state(
                "No farms registered yet",
                "Register a farm to begin organizing records.",
            )
        else:
            for farm in farms:
                with st.expander(
                    f"{farm['farm_name']} — {farm.get('location') or 'No location'}",
                    expanded=False,
                ):
                    col1, col2 = form_columns(2)
                    with col1:
                        st.markdown(f"**Farmer:** {farm['farmer_name']}")
                        st.markdown(
                            f"**Production type:** {farm.get('production_type') or '—'}"
                        )
                        st.markdown(f"**Location:** {farm.get('location') or '—'}")
                    with col2:
                        st.markdown(f"**Phone:** {farm.get('phone') or '—'}")
                        st.markdown(f"**Email:** {farm.get('email') or '—'}")
                        registered = farm.get("created_at", "")[:10]
                        st.markdown(f"**Registered:** {registered}")

    # -----------------------------------------------------------------------
    # TAB: Flock Management
    # -----------------------------------------------------------------------

    with tab_flocks:
        render_section_header(
            "Flock Management", "Keep each production group organized."
        )

        farm_id = st.session_state.selected_farm_id
        if farm_id is None:
            st.info("Select a farm from the sidebar to manage its flocks.")
        else:
            farm = get_farm_service().get_farm(farm_id)
            st.caption(f"Farm: **{farm['farm_name']}**" if farm else "")

            with st.expander("➕ Register a new flock", expanded=False):
                with st.form("register_flock_form", clear_on_submit=True):
                    col1, col2 = form_columns(2)
                    with col1:
                        new_flock_name = st.text_input("Flock name *")
                        new_species = st.selectbox(
                            "Species *",
                            [
                                "Chicken",
                                "Turkey",
                                "Duck",
                                "Quail",
                                "Guinea Fowl",
                                "Goose",
                            ],
                        )
                        new_flock_production_type = st.selectbox(
                            "Production type",
                            [
                                "",
                                "Broiler",
                                "Layer",
                                "Breeder",
                                "Dual Purpose",
                                "Other",
                            ],
                        )
                    with col2:
                        new_breed = st.text_input("Breed (optional)")
                        new_initial_count = st.number_input(
                            "Initial bird count *", min_value=1, step=1, value=100
                        )
                        new_stocking_date = st.date_input(
                            "Stocking date *", value=date.today()
                        )
                        new_flock_status = st.selectbox(
                            "Status", ["active", "closed", "sold"]
                        )

                    if st.form_submit_button("Register flock", type="primary"):
                        try:
                            flock_id = get_farm_service().create_flock(
                                farm_id=farm_id,
                                flock_name=new_flock_name,
                                species=new_species,
                                production_type=new_flock_production_type or None,
                                breed=new_breed or None,
                                initial_count=int(new_initial_count),
                                stocking_date=new_stocking_date,
                                status=new_flock_status,
                            )
                            render_feedback(
                                "success",
                                f"Flock registered successfully (ID: {flock_id}).",
                            )
                            st.cache_resource.clear()
                            st.rerun()
                        except ValueError as exc:
                            render_feedback("error", str(exc))

            flocks = get_farm_service().list_flocks(farm_id)
            if not flocks:
                render_empty_state(
                    "No flocks registered", "Register a flock for the selected farm."
                )
            else:
                for flock in flocks:
                    with st.expander(
                        f"{flock['flock_name']} — "
                        f"{flock['species']} | {flock['initial_count']} birds",
                        expanded=False,
                    ):
                        col1, col2 = form_columns(2)
                        with col1:
                            st.markdown(f"**Species:** {flock['species']}")
                            prod = flock.get("production_type") or "—"
                            st.markdown(f"**Production type:** {prod}")
                            st.markdown(f"**Breed:** {flock.get('breed') or '—'}")
                        with col2:
                            st.markdown(f"**Initial count:** {flock['initial_count']}")
                            sd = flock.get("stocking_date") or "—"
                            st.markdown(f"**Stocking date:** {sd}")
                            st.markdown("**Status**")
                            render_status_label(flock.get("status", "unknown"))

    # -----------------------------------------------------------------------
    # TAB: Daily Records
    # -----------------------------------------------------------------------

    with tab_records:
        render_section_header(
            "Daily Farm Records", "Record daily production and housing conditions."
        )

        flock_id = st.session_state.selected_flock_id
        if flock_id is None:
            st.info("Select a farm and flock from the sidebar to enter daily records.")
        else:
            flock = get_farm_service().get_flock(flock_id)
            st.caption(
                f"Flock: **{flock['flock_name']}** | "
                f"Initial count: {flock['initial_count']} birds"
                if flock
                else ""
            )

            with st.expander("➕ Add a daily record", expanded=True):
                st.caption(
                    "Leave a measurement blank when it was not recorded. "
                    "Enter zero only when zero was genuinely measured."
                )
                with st.form("daily_record_form", clear_on_submit=True):
                    col1, col2, col3 = form_columns(3)
                    with col1:
                        rec_date = st.date_input("Record date *", value=date.today())
                        rec_mortality = st.number_input(
                            "Mortality (birds died)", min_value=0, step=1, value=0
                        )
                        rec_feed = st.number_input(
                            "Feed consumed (kg)",
                            min_value=0.0,
                            step=0.5,
                            value=None,
                            placeholder="Not recorded",
                            format="%.2f",
                        )
                    with col2:
                        rec_water = st.number_input(
                            "Water consumed (litres)",
                            min_value=0.0,
                            step=0.5,
                            value=None,
                            placeholder="Not recorded",
                            format="%.2f",
                        )
                        rec_weight = st.number_input(
                            "Average bird weight (kg)",
                            min_value=0.0,
                            step=0.01,
                            value=None,
                            placeholder="Not recorded",
                            format="%.3f",
                        )
                    with col3:
                        rec_temp = st.number_input(
                            "Temperature (°C)",
                            min_value=-10.0,
                            max_value=60.0,
                            step=0.5,
                            value=None,
                            placeholder="Not recorded",
                            format="%.1f",
                        )
                        rec_humidity = st.number_input(
                            "Humidity (%)",
                            min_value=0.0,
                            max_value=100.0,
                            step=1.0,
                            value=None,
                            placeholder="Not recorded",
                            format="%.1f",
                        )

                    rec_notes = st.text_area("Observations / notes", height=70)

                    if st.form_submit_button("Save record", type="primary"):
                        try:
                            record_id = get_farm_service().create_daily_record(
                                flock_id=flock_id,
                                record_date=rec_date,
                                feed_kg=rec_feed,
                                water_litres=rec_water,
                                mortality=int(rec_mortality),
                                average_weight_kg=rec_weight,
                                temperature_c=rec_temp,
                                humidity_percent=rec_humidity,
                                notes=rec_notes.strip() or None,
                            )
                            render_feedback(
                                "success",
                                f"Daily record saved successfully (ID: {record_id}).",
                            )
                            st.rerun()
                        except DuplicateRecordError as exc:
                            render_feedback("warning", str(exc))
                        except ValueError as exc:
                            render_feedback("error", str(exc))

            st.divider()
            st.markdown("**Recorded entries (most recent first)**")
            records = get_farm_service().get_daily_records(flock_id)
            if not records:
                render_empty_state(
                    "No daily records yet",
                    "Save a daily record to start this flock's history.",
                )
            else:
                display_records = list(reversed(records))
                rows = []
                for r in display_records:
                    # Use explicit None check so 0.0 is shown, not hidden
                    def _fmt(v: object) -> object:
                        return v if v is not None else "—"

                    rows.append(
                        {
                            "Date": r["record_date"],
                            "Mortality": r["mortality"],
                            "Feed (kg)": _fmt(r.get("feed_kg")),
                            "Water (L)": _fmt(r.get("water_litres")),
                            "Avg weight (kg)": _fmt(r.get("average_weight_kg")),
                            "Temp (°C)": _fmt(r.get("temperature_c")),
                            "Humidity (%)": _fmt(r.get("humidity_percent")),
                            "Notes": r.get("notes") or "",
                        }
                    )
                render_data_table(rows)

    # -----------------------------------------------------------------------
    # TAB: Analytics
    # -----------------------------------------------------------------------

    with tab_analytics:
        render_section_header(
            "Flock Analytics", "Descriptive performance from recorded daily records."
        )

        flock_id = st.session_state.selected_flock_id
        if flock_id is None:
            st.info("Select a farm and flock from the sidebar to view analytics.")
        else:
            try:
                analytics = get_analytics_service()
                summary = analytics.get_flock_summary(flock_id)
                metrics = analytics.get_daily_metrics(flock_id)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

            # ------------------------------------------------------------------
            # Summary metric cards
            # ------------------------------------------------------------------
            prod_type = summary.get("production_type") or ""
            flock_label = f"{summary['flock_name']} — {summary['species']}" + (
                f" | {prod_type}" if prod_type else ""
            )
            st.markdown(f"**{flock_label}**")

            kpi_columns = st.columns(5)
            kpi_cards = (
                (
                    "Initial birds",
                    f"{summary['initial_count']:,}",
                    "Starting flock population",
                ),
                (
                    "Current birds",
                    f"{int(summary['current_flock_size']):,}",
                    f"{int(summary['total_mortality'])} recorded mortality",
                ),
                (
                    "Mortality rate",
                    f"{summary['mortality_rate_percent']}%",
                    "Recorded mortality ÷ initial count",
                ),
                (
                    "Total feed",
                    f"{summary['total_feed_kg']} kg",
                    "Sum of recorded feed",
                ),
                (
                    "Total water",
                    f"{summary['total_water_litres']} L",
                    "Sum of recorded water",
                ),
            )
            for column, card in zip(kpi_columns, kpi_cards, strict=True):
                with column:
                    render_kpi_card(*card)

            kpi_columns = st.columns(4)
            kpi_cards = (
                (
                    "Average weight",
                    f"{summary['average_weight_kg']} kg"
                    if summary["average_weight_kg"] is not None
                    else "Not recorded",
                    "Mean of recorded average weights",
                ),
                (
                    "Average temperature",
                    f"{summary['average_temperature_c']} °C"
                    if summary["average_temperature_c"] is not None
                    else "Not recorded",
                    None,
                ),
                (
                    "Average humidity",
                    f"{summary['average_humidity_percent']}%"
                    if summary["average_humidity_percent"] is not None
                    else "Not recorded",
                    None,
                ),
                ("Daily records", summary["record_count"], None),
            )
            for column, card in zip(kpi_columns, kpi_cards, strict=True):
                with column:
                    render_kpi_card(*card)

            if not metrics:
                render_empty_state(
                    "No analytics yet",
                    "Add records in Daily Records to see this flock's charts.",
                )
            else:
                # ----------------------------------------------------------
                # Environmental Monitoring Overview
                # ----------------------------------------------------------
                import pandas as pd

                env = analytics.get_environmental_summary(flock_id)
                t = env["temperature"]
                h = env["humidity"]

                st.divider()
                st.markdown("**Environmental Monitoring Overview**")
                st.caption(
                    "Environmental measurements are currently entered manually "
                    "through daily farm records. "
                    "Live sensor monitoring is not yet connected."
                )

                def _fmt_env(v: object, unit: str = "") -> str:
                    """Format an environmental value or return an em dash."""
                    if v is None:
                        return "—"
                    return f"{v}{unit}"

                def _fmt_date(d: object) -> str:
                    """Format a YYYY-MM-DD date string as DD Mon YYYY."""
                    if d is None:
                        return "—"
                    from datetime import datetime as _dt

                    return _dt.strptime(str(d), "%Y-%m-%d").strftime("%d %b %Y")

                env_col_t, env_col_h = st.columns(2)

                with env_col_t:
                    st.markdown("**Temperature Monitoring**")
                    tc1, tc2, tc3 = st.columns(3)
                    tc1.metric("Average (\u00b0C)", _fmt_env(t["average_c"]))
                    tc2.metric("Minimum (\u00b0C)", _fmt_env(t["minimum_c"]))
                    tc3.metric("Maximum (\u00b0C)", _fmt_env(t["maximum_c"]))
                    tc4, tc5, tc6 = st.columns(3)
                    tc4.metric("Recorded", t["recorded_count"])
                    tc5.metric("Missing", t["missing_count"])
                    tc6.metric("Coverage", _fmt_env(t["coverage_percent"], "%"))
                    if t["latest_value_c"] is not None:
                        st.caption(
                            f"Latest: {t['latest_value_c']} \u00b0C "
                            f"on {_fmt_date(t['latest_record_date'])}"
                        )
                    else:
                        st.caption("No temperature observations recorded.")

                with env_col_h:
                    st.markdown("**Relative Humidity Monitoring**")
                    hc1, hc2, hc3 = st.columns(3)
                    hc1.metric("Average (%)", _fmt_env(h["average_percent"]))
                    hc2.metric("Minimum (%)", _fmt_env(h["minimum_percent"]))
                    hc3.metric("Maximum (%)", _fmt_env(h["maximum_percent"]))
                    hc4, hc5, hc6 = st.columns(3)
                    hc4.metric("Recorded", h["recorded_count"])
                    hc5.metric("Missing", h["missing_count"])
                    hc6.metric("Coverage", _fmt_env(h["coverage_percent"], "%"))
                    if h["latest_value_percent"] is not None:
                        st.caption(
                            f"Latest: {h['latest_value_percent']} % "
                            f"on {_fmt_date(h['latest_record_date'])}"
                        )
                    else:
                        st.caption("No humidity observations recorded.")

                def _altair_chart(
                    data: pd.DataFrame,
                    col: str,
                    chart_type: str,
                    colour: str,
                    *,
                    zero_baseline: bool = False,
                ) -> alt.Chart:
                    """Return an Altair bar or line+point chart."""
                    plot_df = data.copy()
                    plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")
                    plot_df = plot_df[plot_df[col].notna()].reset_index(drop=True)

                    y_scale = alt.Scale(domainMin=0) if zero_baseline else alt.Undefined
                    y_enc = alt.Y(f"{col}:Q", title=None, scale=y_scale)
                    x_enc = alt.X("record_date:T", title=None)
                    tooltip = [
                        alt.Tooltip("record_date:T", title="Date", format="%d %b %Y"),
                        alt.Tooltip(f"{col}:Q", title=col),
                    ]

                    base = alt.Chart(plot_df).encode(x=x_enc, tooltip=tooltip)

                    if chart_type == "bar":
                        return base.mark_bar(color=colour).encode(y=y_enc)

                    line = base.mark_line(color=colour).encode(y=y_enc)
                    points = base.mark_point(color=colour, filled=True, size=60).encode(
                        y=y_enc
                    )
                    return line + points

                df = pd.DataFrame(metrics)
                # Ensure dates are parsed and sorted oldest-first
                df["record_date"] = pd.to_datetime(df["record_date"], format="%Y-%m-%d")
                df = df.sort_values("record_date").reset_index(drop=True)

                # Cast numeric columns explicitly to avoid object-dtype issues
                for col in (
                    "mortality",
                    "cumulative_mortality",
                    "current_flock_size",
                ):
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                st.divider()

                # ----------------------------------------------------------
                # Row 1: Daily mortality bar | Cumulative mortality line
                # Separated so the small cumulative values are readable.
                # ----------------------------------------------------------
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Daily mortality** — birds lost per day")
                    st.altair_chart(
                        _altair_chart(
                            df, "mortality", "bar", CHART_COLORS["mortality"]
                        ),
                        use_container_width=True,
                    )
                with col_b:
                    st.markdown(
                        "**Cumulative mortality** — running total of birds lost"
                    )
                    st.altair_chart(
                        _altair_chart(
                            df,
                            "cumulative_mortality",
                            "line",
                            CHART_COLORS["mortality"],
                        ),
                        use_container_width=True,
                    )

                # ----------------------------------------------------------
                # Row 2: Remaining flock population
                # Separate chart so scale is not distorted by mortality.
                # ----------------------------------------------------------
                st.markdown("**Remaining flock population** — birds alive over time")
                st.altair_chart(
                    _altair_chart(
                        df,
                        "current_flock_size",
                        "line",
                        CHART_COLORS["population"],
                        zero_baseline=True,
                    ),
                    use_container_width=True,
                )

                st.divider()

                # ----------------------------------------------------------
                # Row 3: Feed and water — only plot rows where value was
                # actually recorded (not None). 0.0 is a valid measurement.
                # ----------------------------------------------------------
                col_c, col_d = st.columns(2)
                with col_c:
                    st.markdown("**Feed consumed (kg/day)**")
                    feed_df = df[df["feed_kg"].notna()]
                    if not feed_df.empty:
                        st.altair_chart(
                            _altair_chart(
                                feed_df, "feed_kg", "bar", CHART_COLORS["feed"]
                            ),
                            use_container_width=True,
                        )
                    else:
                        render_empty_state(
                            "No feed measurements", "No feed values are recorded yet."
                        )
                with col_d:
                    st.markdown("**Water consumed (litres/day)**")
                    water_df = df[df["water_litres"].notna()]
                    if not water_df.empty:
                        st.altair_chart(
                            _altair_chart(
                                water_df, "water_litres", "bar", CHART_COLORS["water"]
                            ),
                            use_container_width=True,
                        )
                    else:
                        render_empty_state(
                            "No water measurements", "No water values are recorded yet."
                        )

                # ----------------------------------------------------------
                # Row 4: Weight, temperature, humidity
                # ----------------------------------------------------------
                col_e, col_f, col_g = st.columns(3)
                with col_e:
                    st.markdown("**Average bird weight (kg)**")
                    wt_df = df[df["average_weight_kg"].notna()]
                    if not wt_df.empty:
                        # Flag any weight below 0.1 kg as potentially
                        # suspicious so the user can review the entry.
                        low_wt = wt_df[wt_df["average_weight_kg"] < 0.1]
                        if not low_wt.empty:
                            dates = ", ".join(
                                d.strftime("%d %b %Y") for d in low_wt["record_date"]
                            )
                            st.warning(
                                f"⚠️ Weight below 0.1 kg recorded on: {dates}. "
                                "Please verify the entry is in kilograms."
                            )
                        st.altair_chart(
                            _altair_chart(
                                wt_df,
                                "average_weight_kg",
                                "line",
                                CHART_COLORS["weight"],
                            ),
                            use_container_width=True,
                        )
                    else:
                        st.caption("No weight measurements recorded for this flock.")
                with col_f:
                    st.markdown("**House temperature (°C)**")
                    tmp_df = df[df["temperature_c"].notna()]
                    if not tmp_df.empty:
                        st.altair_chart(
                            _altair_chart(
                                tmp_df,
                                "temperature_c",
                                "line",
                                CHART_COLORS["temperature"],
                            ),
                            use_container_width=True,
                        )
                    else:
                        st.caption(
                            "No temperature measurements recorded for this flock."
                        )
                with col_g:
                    st.markdown("**Relative humidity (%)**")
                    hum_df = df[df["humidity_percent"].notna()]
                    if not hum_df.empty:
                        st.altair_chart(
                            _altair_chart(
                                hum_df,
                                "humidity_percent",
                                "line",
                                CHART_COLORS["humidity"],
                            ),
                            use_container_width=True,
                        )
                    else:
                        st.caption("No humidity measurements recorded for this flock.")

                # ----------------------------------------------------------
                # Full daily metrics table
                # ----------------------------------------------------------
                st.divider()
                st.markdown("**Full daily metrics — all values as stored**")

                def _fmt_val(v: object) -> object:
                    """Show None as — without hiding 0.0."""
                    return v if v is not None else "—"

                table_rows = [
                    {
                        "Date": row["record_date"].strftime("%d %b %Y"),
                        "Daily mortality": int(row["mortality"]),
                        "Cumul. mortality": int(row["cumulative_mortality"]),
                        "Flock size": int(row["current_flock_size"]),
                        "Mortality %": row["mortality_rate_percent"],
                        "Feed (kg)": _fmt_val(row["feed_kg"]),
                        "Water (L)": _fmt_val(row["water_litres"]),
                        "Avg weight (kg)": _fmt_val(row["average_weight_kg"]),
                        "Temp (°C)": _fmt_val(row["temperature_c"]),
                        "Humidity (%)": _fmt_val(row["humidity_percent"]),
                        "Notes": row["notes"] or "",
                    }
                    for _, row in df.iterrows()
                ]
                render_data_table(table_rows)

    st.divider()
    st.markdown(
        (
            '<div class="pg-footer">'
            "Farm Intelligence · Local records are stored in SQLite · "
            f"{datetime.now().strftime('%Y-%m-%d')}</div>"
        ),
        unsafe_allow_html=True,
    )
