"""Shared visual tokens and reusable Streamlit presentation helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from html import escape

import streamlit as st

COLORS = {
    "forest": "#163B2F",
    "emerald": "#1F8A5B",
    "primary_action": "#177548",
    "teal": "#247C7A",
    "mint": "#E8F4EE",
    "canvas": "#F7F9F7",
    "charcoal": "#1F2933",
    "slate": "#667085",
    "amber": "#C78B27",
    "amber_data": "#946200",
    "red": "#C43D3D",
    "white": "#FFFFFF",
    "success": "#287A4B",
    "warning": "#9A6500",
    "error": "#B42318",
    "info": "#247C7A",
    "border": "#DCE6DF",
    "border_strong": "#B7CABB",
    "mint_border": "#CDE3D5",
    "on_forest": "#F4F8F5",
    "forest_muted": "#D5E6DB",
    "focus": "#67B58E",
    "success_surface": "#E6F4EA",
    "success_text": "#205B36",
    "warning_surface": "#FFF3D6",
    "warning_text": "#704B00",
    "error_surface": "#FDE8E7",
    "error_text": "#8A1C13",
    "neutral_surface": "#E9EEF2",
    "neutral_text": "#344054",
}

CHART_COLORS = {
    "mortality": COLORS["red"],
    "population": COLORS["emerald"],
    "feed": COLORS["amber_data"],
    "water": COLORS["teal"],
    "weight": COLORS["emerald"],
    "temperature": COLORS["amber_data"],
    "humidity": COLORS["teal"],
}


def apply_design_system() -> None:
    """Apply the shared shell, typography, surface and control styling."""
    st.markdown(
        f"""
        <style>
        :root {{
            --pg-forest: {COLORS["forest"]};
            --pg-emerald: {COLORS["emerald"]};
            --pg-teal: {COLORS["teal"]};
            --pg-mint: {COLORS["mint"]};
            --pg-canvas: {COLORS["canvas"]};
            --pg-charcoal: {COLORS["charcoal"]};
            --pg-slate: {COLORS["slate"]};
            --pg-amber: {COLORS["amber"]};
            --pg-red: {COLORS["red"]};
            --pg-white: {COLORS["white"]};
            --pg-border: {COLORS["border"]};
            --pg-border-strong: {COLORS["border_strong"]};
            --pg-mint-border: {COLORS["mint_border"]};
            --pg-on-forest: {COLORS["on_forest"]};
            --pg-forest-muted: {COLORS["forest_muted"]};
            --pg-focus: {COLORS["focus"]};
            --pg-success-surface: {COLORS["success_surface"]};
            --pg-success-text: {COLORS["success_text"]};
            --pg-warning-surface: {COLORS["warning_surface"]};
            --pg-warning-text: {COLORS["warning_text"]};
            --pg-error-surface: {COLORS["error_surface"]};
            --pg-error-text: {COLORS["error_text"]};
            --pg-neutral-surface: {COLORS["neutral_surface"]};
            --pg-neutral-text: {COLORS["neutral_text"]};
        }}
        html, body, [class*="stApp"] {{
            font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                         BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--pg-charcoal);
        }}
        .stApp {{ background: var(--pg-canvas); }}
        [data-testid="stMainBlockContainer"] {{ padding-top: 1.5rem; }}
        [data-testid="stSidebar"] {{
            background: var(--pg-forest);
            border-right: 1px solid rgba(255, 255, 255, 0.12);
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] small {{ color: var(--pg-on-forest); }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {{
            border-radius: 0.55rem;
            padding: 0.35rem 0.5rem;
        }}
        h1, h2, h3 {{ color: var(--pg-forest); letter-spacing: -0.025em; }}
        h1 {{ font-size: clamp(1.65rem, 3vw, 2.2rem); font-weight: 700; }}
        h2 {{ font-size: clamp(1.2rem, 2vw, 1.5rem); font-weight: 650; }}
        [data-testid="stForm"], [data-testid="stExpander"] {{
            border: 1px solid var(--pg-border);
            border-radius: 0.85rem;
            background: var(--pg-white);
        }}
        [data-testid="stForm"] {{ padding: 1rem 1.1rem; }}
        [data-testid="stMetric"] {{
            background: var(--pg-white);
            border: 1px solid var(--pg-border);
            border-radius: 0.85rem;
            padding: 1rem 1.1rem;
            min-height: 6.5rem;
        }}
        [data-testid="stMetricLabel"] p {{ color: var(--pg-slate); }}
        [data-testid="stMetricValue"] {{ color: var(--pg-forest); }}
        [data-testid="stBaseButton-primary"] {{
            background: {COLORS["primary_action"]};
            border-color: {COLORS["primary_action"]};
            color: var(--pg-white);
            border-radius: 0.6rem;
            font-weight: 650;
        }}
        [data-testid="stBaseButton-primary"]:hover {{
            background: var(--pg-forest);
            border-color: var(--pg-forest);
            color: var(--pg-white);
        }}
        [data-testid="stDataFrame"] {{
            border: 1px solid var(--pg-border);
            border-radius: 0.75rem;
            overflow: hidden;
        }}
        [data-testid="stWidgetLabel"] p {{ color: var(--pg-charcoal); }}
        :focus-visible {{
            outline: 3px solid var(--pg-focus) !important;
            outline-offset: 2px;
        }}
        .pg-brand {{ display: flex; align-items: center; gap: 0.65rem; }}
        .pg-brand-mark {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 2.35rem; height: 2.35rem; border-radius: 0.7rem;
            background: var(--pg-mint); color: var(--pg-forest);
            font-size: 0.95rem; font-weight: 800; letter-spacing: -0.04em;
        }}
        .pg-brand-name {{
            color: var(--pg-white);
            font-size: 1.08rem;
            font-weight: 750;
        }}
        .pg-brand-tagline {{
            color: var(--pg-forest-muted);
            font-size: 0.76rem;
            margin-top: 0.12rem;
        }}
        .pg-app-header {{
            display: flex; justify-content: space-between; align-items: center;
            gap: 1rem; flex-wrap: wrap; background: var(--pg-white);
            border: 1px solid var(--pg-border); border-radius: 0.9rem;
            padding: 0.85rem 1.1rem; margin: 0 0 1.4rem;
        }}
        .pg-app-header-title {{
            color: var(--pg-forest);
            font-size: 0.9rem;
            font-weight: 700;
        }}
        .pg-app-header-context {{
            color: var(--pg-slate);
            font-size: 0.82rem;
            margin-top: 0.15rem;
        }}
        .pg-context-pill {{
            display: inline-flex; align-items: center; gap: 0.4rem;
            background: var(--pg-mint); color: var(--pg-forest);
            border: 1px solid var(--pg-mint-border); border-radius: 99px;
            padding: 0.42rem 0.75rem; font-size: 0.82rem; font-weight: 650;
        }}
        .pg-page-title {{
            color: var(--pg-forest);
            font-size: clamp(1.75rem, 3vw, 2.35rem);
            font-weight: 750;
            letter-spacing: -0.035em;
            margin: 0 0 0.35rem;
        }}
        .pg-page-subtitle {{
            color: var(--pg-slate);
            font-size: 1rem;
            line-height: 1.55;
            margin: 0 0 1.3rem;
        }}
        .pg-section-title {{
            color: var(--pg-forest);
            font-size: 1.2rem;
            font-weight: 700;
            margin: 0.4rem 0 0.3rem;
        }}
        .pg-section-help {{
            color: var(--pg-slate);
            font-size: 0.88rem;
            margin: 0 0 0.75rem;
        }}
        .pg-kpi {{
            background: var(--pg-white);
            border: 1px solid var(--pg-border);
            border-radius: 0.85rem;
            padding: 1rem 1.1rem;
            min-height: 6.2rem;
        }}
        .pg-kpi-label {{
            color: var(--pg-slate);
            font-size: 0.82rem;
            font-weight: 600;
        }}
        .pg-kpi-value {{
            color: var(--pg-forest);
            font-size: 1.55rem;
            font-weight: 750;
            letter-spacing: -0.025em;
            margin-top: 0.42rem;
        }}
        .pg-kpi-detail {{
            color: var(--pg-slate);
            font-size: 0.78rem;
            line-height: 1.4;
            margin-top: 0.2rem;
        }}
        .pg-empty {{
            background: var(--pg-white);
            border: 1px dashed var(--pg-border-strong);
            border-radius: 0.85rem;
            padding: 1rem 1.1rem;
        }}
        .pg-empty-title {{
            color: var(--pg-forest);
            font-weight: 700;
            margin-bottom: 0.2rem;
        }}
        .pg-empty-body {{
            color: var(--pg-slate);
            font-size: 0.9rem;
            line-height: 1.5;
        }}
        .pg-status {{
            display: inline-block;
            border-radius: 99px;
            padding: 0.2rem 0.6rem;
            font-size: 0.78rem;
            font-weight: 650;
        }}
        .pg-status-success {{
            background: var(--pg-success-surface);
            color: var(--pg-success-text);
        }}
        .pg-status-warning {{
            background: var(--pg-warning-surface);
            color: var(--pg-warning-text);
        }}
        .pg-status-error {{
            background: var(--pg-error-surface);
            color: var(--pg-error-text);
        }}
        .pg-status-neutral {{
            background: var(--pg-neutral-surface);
            color: var(--pg-neutral-text);
        }}
        .pg-footer {{
            color: var(--pg-slate);
            font-size: 0.78rem;
            border-top: 1px solid var(--pg-border);
            padding-top: 0.7rem;
        }}
        @media (max-width: 640px) {{
            [data-testid="stMainBlockContainer"] {{ padding: 1rem 1rem 1.5rem; }}
            [data-testid="stHorizontalBlock"] {{ flex-direction: column; }}
            [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                flex: 1 1 auto !important;
                width: 100% !important;
            }}
            .pg-app-header {{ align-items: flex-start; padding: 0.8rem; }}
            .pg-kpi {{ padding: 0.85rem; min-height: auto; }}
            .pg-kpi-value {{ font-size: 1.35rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    """Render a consistent sidebar wordmark and product tagline."""
    st.markdown(
        """
        <div class="pg-brand" aria-label="PoultryGuard AI">
          <span class="pg-brand-mark" aria-hidden="true">PG</span>
          <div>
            <div class="pg-brand-name">PoultryGuard AI</div>
            <div class="pg-brand-tagline">
              Intelligent Poultry Farming. Better Decisions.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_navigation(options: list[str], key: str) -> str:
    """Render the existing top-level navigation with a visible input label."""
    return st.radio("Navigation", options, key=key, label_visibility="collapsed")


def render_app_header(section: str, active_farm: str | None = None) -> None:
    """Show the current product area and active farm context."""
    if active_farm:
        context = f"Active farm: {escape(active_farm)}"
    elif section == "Farm Intelligence":
        context = "Select a farm"
    else:
        context = "Local workspace"
    st.markdown(
        f"""
        <header class="pg-app-header">
          <div>
            <div class="pg-app-header-title">{escape(section)}</div>
            <div class="pg-app-header-context">
              Intelligent Poultry Farming. Better Decisions.
            </div>
          </div>
          <div class="pg-context-pill">{context}</div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str) -> None:
    """Render a page title with a consistent explanatory subtitle."""
    st.markdown(
        f'<h1 class="pg-page-title">{escape(title)}</h1>'
        f'<p class="pg-page-subtitle">{escape(subtitle)}</p>',
        unsafe_allow_html=True,
    )


def render_section_header(title: str, help_text: str | None = None) -> None:
    """Render a consistent section heading and optional supporting text."""
    description = (
        f'<p class="pg-section-help">{escape(help_text)}</p>' if help_text else ""
    )
    st.markdown(
        f'<h2 class="pg-section-title">{escape(title)}</h2>{description}',
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: object, detail: str | None = None) -> None:
    """Render a semantic KPI card with optional explanatory detail."""
    detail_html = f'<div class="pg-kpi-detail">{escape(detail)}</div>' if detail else ""
    st.markdown(
        f"""
        <div class="pg-kpi" role="group" aria-label="{escape(label)}">
          <div class="pg-kpi-label">{escape(label)}</div>
          <div class="pg-kpi-value">{escape(str(value))}</div>
          {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, message: str) -> None:
    """Render a calm empty-state card with a clear next-step message."""
    st.markdown(
        f"""
        <div class="pg-empty" role="status">
          <div class="pg-empty-title">{escape(title)}</div>
          <div class="pg-empty-body">{escape(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_label(status: str, label: str | None = None) -> None:
    """Render a text-labeled status badge; meaning never depends on color alone."""
    normalized = status.strip().lower()
    state_class = {
        "active": "success",
        "success": "success",
        "closed": "neutral",
        "sold": "neutral",
        "pending": "warning",
        "pending_validation": "warning",
        "warning": "warning",
        "invalid": "error",
        "rejected": "error",
        "error": "error",
    }.get(normalized, "neutral")
    visible_label = label or status.replace("_", " ").title()
    st.markdown(
        f'<span class="pg-status pg-status-{state_class}" role="status">'
        f"{escape(visible_label)}</span>",
        unsafe_allow_html=True,
    )


def render_feedback(kind: str, message: str) -> None:
    """Render Streamlit's accessible message component for the selected state."""
    handlers = {
        "success": st.success,
        "info": st.info,
        "warning": st.warning,
        "error": st.error,
    }
    if kind not in handlers:
        raise ValueError(f"Unsupported feedback kind: {kind}")
    handlers[kind](message)


def render_data_table(data: object) -> None:
    """Render a consistently sized, index-free data table."""
    st.dataframe(data, use_container_width=True, hide_index=True)


def form_columns(count: int) -> list[object]:
    """Return consistently spaced responsive columns for form layouts."""
    return st.columns(count, gap="large")


@contextmanager
def loading_indicator(message: str) -> Iterator[None]:
    """Use Streamlit's native spinner with consistent application wording."""
    with st.spinner(message):
        yield
