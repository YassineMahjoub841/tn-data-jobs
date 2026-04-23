"""Streamlit dashboard for tn-data-jobs."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = Path("data/marts.duckdb")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TN Data Jobs — Weekly Insights",
    page_icon="📊",
    layout="wide",
)

st.title("📊 TN Data Jobs — Weekly Insights")
st.caption(
    "Automated weekly snapshot of data & AI job demand in Tunisia and France. "
    "Source: TanitJobs + France Travail."
)


# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_skills() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("SELECT * FROM marts.dim_skills ORDER BY posting_count DESC").df()
    con.close()
    return df


@st.cache_data(ttl=3600)
def load_companies() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("SELECT * FROM marts.dim_companies ORDER BY total_postings DESC").df()
    con.close()
    return df


@st.cache_data(ttl=3600)
def load_postings() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(
        "SELECT posting_id, source, title, company_name, location, "
        "contract_type, posted_date, skills FROM marts.fct_postings "
        "ORDER BY posted_date DESC NULLS LAST"
    ).df()
    con.close()
    return df


# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    source_filter = st.multiselect(
        "Source",
        options=["tanitjobs", "france_travail"],
        default=["tanitjobs", "france_travail"],
    )
    top_n = st.slider("Top N skills", min_value=5, max_value=50, value=20)

# ── Load data ──────────────────────────────────────────────────────────────────
try:
    df_skills = load_skills()
    df_companies = load_companies()
    df_postings = load_postings()
    data_available = True
except Exception as exc:
    st.warning(
        f"Could not load data from `{DB_PATH}`. "
        "Run the pipeline first (`dbt run`) to generate the mart tables.\n\n"
        f"Error: {exc}"
    )
    data_available = False

if data_available:
    # ── KPI row ────────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    filtered_postings = df_postings[df_postings["source"].isin(source_filter)]
    col1.metric("Total postings", f"{len(filtered_postings):,}")
    col2.metric("Unique companies", f"{filtered_postings['company_name'].nunique():,}")
    col3.metric("Unique skills", f"{df_skills.shape[0]:,}")
    col4.metric(
        "Latest scrape",
        str(df_postings["posted_date"].max()) if not df_postings.empty else "—",
    )

    st.divider()

    # ── Top skills ─────────────────────────────────────────────────────────────
    st.subheader(f"Top {top_n} In-Demand Skills")
    top_skills = df_skills.head(top_n)
    st.bar_chart(top_skills.set_index("skill_name")["posting_count"])

    st.divider()

    # ── Skills split by source ─────────────────────────────────────────────────
    st.subheader("Skills split by source")
    split_df = top_skills[["skill_name", "tanitjobs_count", "france_travail_count"]].set_index(
        "skill_name"
    )
    st.bar_chart(split_df)

    st.divider()

    # ── Companies ─────────────────────────────────────────────────────────────
    st.subheader("Top Hiring Companies")
    st.dataframe(
        df_companies.head(20)[
            ["company_name", "total_postings", "tanitjobs_postings", "france_travail_postings", "latest_posting_date"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Raw postings explorer ──────────────────────────────────────────────────
    st.subheader("Postings Explorer")
    search = st.text_input("Search titles / companies", placeholder="e.g. data engineer")
    display_df = filtered_postings.copy()
    if search:
        mask = (
            display_df["title"].str.contains(search, case=False, na=False)
            | display_df["company_name"].str.contains(search, case=False, na=False)
        )
        display_df = display_df[mask]

    st.dataframe(
        display_df[["title", "company_name", "location", "contract_type", "posted_date", "source"]],
        use_container_width=True,
        hide_index=True,
    )
