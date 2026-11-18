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

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("# 🐔 PoultryGuard AI")
    st.caption("Farm Intelligence MVP")
    st.divider()

    section = st.radio(
        "Navigation",
        ["Knowledge Assistant", "Farm Intelligence"],
        key="nav_section",
        label_visibility="collapsed",
    )

    if section == "Farm Intelligence":
        st.divider()
        farms = get_farm_service().list_farms()
        if farms:
            farm_options = {f["farm_name"]: f["id"] for f in farms}
            selected_name = st.selectbox(
                "Active farm",
                list(farm_options.keys()),
                key="_sidebar_farm_select",
            )
            st.session_state.selected_farm_id = farm_options[selected_name]

            flocks = get_farm_service().list_flocks(st.session_state.selected_farm_id)
            if flocks:
                flock_options = {f["flock_name"]: f["id"] for f in flocks}
                selected_flock = st.selectbox(
                    "Active flock",
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

# ---------------------------------------------------------------------------
# SECTION: Knowledge Assistant
# ---------------------------------------------------------------------------

if section == "Knowledge Assistant":
    st.title("🐔 PoultryGuard AI — Knowledge Assistant")
    st.write(
        "Ask questions about poultry farming, biosecurity, housing, "
        "flock management and other topics covered by the knowledge base."
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
                with st.spinner("Finding relevant evidence..."):
                    passages = get_retriever().search(question.strip(), top_k=top_k)

                if not passages:
                    st.warning(
                        "No relevant passages were found. Try rephrasing "
                        "your question or consult a poultry professional."
                    )
                else:
                    with st.spinner("Generating an evidence-based answer..."):
                        result = get_answer_generator().generate(
                            question=question.strip(), passages=passages
                        )

                    st.subheader("Answer")
                    st.markdown(result.answer)
                    st.subheader("Supporting sources")

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
                st.error(str(exc))
            except Exception as exc:
                st.error(
                    "PoultryGuard could not complete the request. "
                    "Check your API access and terminal output, then try again."
                )
                st.caption(f"{type(exc).__name__}: {exc}")

    st.divider()
    st.caption("PoultryGuard AI | Local knowledge retrieval + Groq answer generation")

# ---------------------------------------------------------------------------
# SECTION: Farm Intelligence
# ---------------------------------------------------------------------------

else:
    st.title("🏡 Farm Intelligence")

    tab_dashboard, tab_farms, tab_flocks, tab_records, tab_analytics = st.tabs(
        ["Dashboard", "Farm Profiles", "Flock Management", "Daily Records", "Analytics"]
    )

    # -----------------------------------------------------------------------
    # TAB: Dashboard
    # -----------------------------------------------------------------------

    with tab_dashboard:
        st.subheader("Farm Dashboard")

        farms = get_farm_service().list_farms()
        if not farms:
            st.info(
                "No farms registered yet. "
                "Go to **Farm Profiles** to register your first farm."
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
                    st.info(
                        "No flocks registered for this farm. "
                        "Go to **Flock Management** to add a flock."
                    )
                else:
                    st.markdown(f"**{len(flocks)} flock(s) registered**")
                    analytics = get_analytics_service()
                    cols = st.columns(min(len(flocks), 3))
                    for idx, flock in enumerate(flocks):
                        with cols[idx % 3]:
                            try:
                                summary = analytics.get_flock_summary(flock["id"])
                                status_icon = (
                                    "🟢" if flock.get("status") == "active" else "⚪"
                                )
                                st.metric(
                                    f"{status_icon} {flock['flock_name']}",
                                    f"{int(summary['current_flock_size'])} birds",
                                    delta=(
                                        f"-{int(summary['total_mortality'])} mortality"
                                    ),
                                    delta_color="normal",
                                )
                                st.caption(
                                    f"{summary['record_count']} record(s) | "
                                    f"{summary['mortality_rate_percent']}%"
                                    " mortality rate"
                                )
                            except Exception:
                                st.metric(flock["flock_name"], "—")

    # -----------------------------------------------------------------------
    # TAB: Farm Profiles
    # -----------------------------------------------------------------------

    with tab_farms:
        st.subheader("Farm Profiles")

        with st.expander("➕ Register a new farm", expanded=False):
            with st.form("register_farm_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
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
                        st.success(f"Farm registered successfully (ID: {farm_id}).")
                        st.cache_resource.clear()
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

        farms = get_farm_service().list_farms()
        if not farms:
            st.info("No farms registered yet.")
        else:
            for farm in farms:
                with st.expander(
                    f"🏡 {farm['farm_name']} — {farm.get('location') or 'No location'}",
                    expanded=False,
                ):
                    col1, col2 = st.columns(2)
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
        st.subheader("Flock Management")

        farm_id = st.session_state.selected_farm_id
        if farm_id is None:
            st.info("Select a farm from the sidebar to manage its flocks.")
        else:
            farm = get_farm_service().get_farm(farm_id)
            st.caption(f"Farm: **{farm['farm_name']}**" if farm else "")

            with st.expander("➕ Register a new flock", expanded=False):
                with st.form("register_flock_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
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
                            st.success(
                                f"Flock registered successfully (ID: {flock_id})."
                            )
                            st.cache_resource.clear()
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

            flocks = get_farm_service().list_flocks(farm_id)
            if not flocks:
                st.info("No flocks registered for this farm.")
            else:
                for flock in flocks:
                    status_icon = "🟢" if flock.get("status") == "active" else "⚪"
                    with st.expander(
                        f"{status_icon} {flock['flock_name']} — "
                        f"{flock['species']} | {flock['initial_count']} birds",
                        expanded=False,
                    ):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Species:** {flock['species']}")
                            prod = flock.get("production_type") or "—"
                            st.markdown(f"**Production type:** {prod}")
                            st.markdown(f"**Breed:** {flock.get('breed') or '—'}")
                        with col2:
                            st.markdown(f"**Initial count:** {flock['initial_count']}")
                            sd = flock.get("stocking_date") or "—"
                            st.markdown(f"**Stocking date:** {sd}")
                            st.markdown(f"**Status:** {flock.get('status', '—')}")

    # -----------------------------------------------------------------------
    # TAB: Daily Records
    # -----------------------------------------------------------------------

    with tab_records:
        st.subheader("Daily Farm Records")

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
                with st.form("daily_record_form", clear_on_submit=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        rec_date = st.date_input("Record date *", value=date.today())
                        rec_mortality = st.number_input(
                            "Mortality (birds died)", min_value=0, step=1, value=0
                        )
                        rec_feed = st.number_input(
                            "Feed consumed (kg)",
                            min_value=0.0,
                            step=0.5,
                            value=0.0,
                            format="%.2f",
                        )
                    with col2:
                        rec_water = st.number_input(
                            "Water consumed (litres)",
                            min_value=0.0,
                            step=0.5,
                            value=0.0,
                            format="%.2f",
                        )
                        rec_weight = st.number_input(
                            "Average bird weight (kg)",
                            min_value=0.0,
                            step=0.01,
                            value=0.0,
                            format="%.3f",
                        )
                    with col3:
                        rec_temp = st.number_input(
                            "Temperature (°C)",
                            min_value=-10.0,
                            max_value=60.0,
                            step=0.5,
                            value=28.0,
                            format="%.1f",
                        )
                        rec_humidity = st.number_input(
                            "Humidity (%)",
                            min_value=0.0,
                            max_value=100.0,
                            step=1.0,
                            value=65.0,
                            format="%.1f",
                        )

                    rec_notes = st.text_area("Observations / notes", height=70)

                    if st.form_submit_button("Save record", type="primary"):
                        try:
                            record_id = get_farm_service().create_daily_record(
                                flock_id=flock_id,
                                record_date=rec_date,
                                feed_kg=rec_feed if rec_feed > 0 else None,
                                water_litres=rec_water if rec_water > 0 else None,
                                mortality=int(rec_mortality),
                                average_weight_kg=(
                                    rec_weight if rec_weight > 0 else None
                                ),
                                temperature_c=rec_temp,
                                humidity_percent=rec_humidity,
                                notes=rec_notes.strip() or None,
                            )
                            st.success(
                                f"Daily record saved successfully (ID: {record_id})."
                            )
                            st.rerun()
                        except DuplicateRecordError as exc:
                            st.warning(str(exc))
                        except ValueError as exc:
                            st.error(str(exc))

            st.divider()
            st.markdown("**Recorded entries (most recent first)**")
            records = get_farm_service().get_daily_records(flock_id)
            if not records:
                st.info("No daily records yet for this flock.")
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
                st.dataframe(rows, use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------------
    # TAB: Analytics
    # -----------------------------------------------------------------------

    with tab_analytics:
        st.subheader("Flock Analytics")

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

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Initial birds", f"{summary['initial_count']:,}")
            c2.metric(
                "Current birds",
                f"{int(summary['current_flock_size']):,}",
                delta=f"-{int(summary['total_mortality'])}",
                delta_color="normal",
                help="Initial count minus total recorded mortality.",
            )
            c3.metric(
                "Mortality rate",
                f"{summary['mortality_rate_percent']}%",
                help="Total mortality ÷ initial count × 100.",
            )
            c4.metric(
                "Total feed (kg)",
                summary["total_feed_kg"],
                help="Sum of all recorded feed_kg values.",
            )
            c5.metric(
                "Total water (L)",
                summary["total_water_litres"],
                help="Sum of all recorded water_litres values.",
            )

            c6, c7, c8, c9 = st.columns(4)
            c6.metric(
                "Avg weight (kg)",
                summary["average_weight_kg"]
                if summary["average_weight_kg"] is not None
                else "—",
                help="Mean of recorded average_weight_kg values.",
            )
            c7.metric(
                "Avg temp (°C)",
                summary["average_temperature_c"]
                if summary["average_temperature_c"] is not None
                else "—",
            )
            c8.metric(
                "Avg humidity (%)",
                summary["average_humidity_percent"]
                if summary["average_humidity_percent"] is not None
                else "—",
            )
            c9.metric("Daily records", summary["record_count"])

            if not metrics:
                st.info(
                    "No daily records yet. "
                    "Add records in the **Daily Records** tab to see charts."
                )
            else:
                import pandas as pd

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
                        _altair_chart(df, "mortality", "bar", "#e05c5c"),
                        use_container_width=True,
                    )
                with col_b:
                    st.markdown(
                        "**Cumulative mortality** — running total of birds lost"
                    )
                    st.altair_chart(
                        _altair_chart(df, "cumulative_mortality", "line", "#e05c5c"),
                        use_container_width=True,
                    )

                # ----------------------------------------------------------
                # Row 2: Remaining flock population
                # Separate chart so scale is not distorted by mortality.
                # ----------------------------------------------------------
                st.markdown("**Remaining flock population** — birds alive over time")
                st.altair_chart(
                    _altair_chart(
                        df, "current_flock_size", "line", "#4caf7d", zero_baseline=True
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
                            _altair_chart(feed_df, "feed_kg", "bar", "#f4a261"),
                            use_container_width=True,
                        )
                    else:
                        st.caption("No feed measurements recorded for this flock.")
                with col_d:
                    st.markdown("**Water consumed (litres/day)**")
                    water_df = df[df["water_litres"].notna()]
                    if not water_df.empty:
                        st.altair_chart(
                            _altair_chart(water_df, "water_litres", "bar", "#457b9d"),
                            use_container_width=True,
                        )
                    else:
                        st.caption("No water measurements recorded for this flock.")

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
                                wt_df, "average_weight_kg", "line", "#6a994e"
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
                            _altair_chart(tmp_df, "temperature_c", "line", "#e76f51"),
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
                                hum_df, "humidity_percent", "line", "#457b9d"
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
                st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()
    st.caption(
        "PoultryGuard AI | Farm Intelligence MVP | "
        f"Data stored locally in SQLite | {datetime.now().strftime('%Y-%m-%d')}"
    )
