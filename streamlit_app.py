import os
import json
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

from app.config import settings
from app.graph.workflow import create_job_discovery_graph
from app.database.connection import get_db_session, init_db
from app.database.repository import DatabaseRepository
from app.database.models import PipelineRunModel, JobMatchModel, ApplicationModel
from app.matching.schema import MatchCategory, ApplicationStatus

# --- Page Configuration ---
st.set_page_config(
    page_title="Job Discovery & Matching Agent",
    page_icon=":briefcase:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    /* Global Typography & Spacing */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header Gradient & Hero styling */
    .hero-container {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F766E 100%);
        padding: 2rem 2.2rem;
        border-radius: 16px;
        color: #FFFFFF;
        margin-bottom: 1.8rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.4rem;
        color: #F8FAFC;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94A3B8;
        max-width: 800px;
        line-height: 1.5;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(20, 184, 166, 0.2);
        color: #2DD4BF;
        border: 1px solid rgba(45, 212, 191, 0.3);
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Metric cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -4px rgba(0,0,0,0.06);
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 0.2rem;
    }

    /* Job Card Styling */
    .job-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .job-card:hover {
        border-color: #0D9488;
        box-shadow: 0 10px 20px -3px rgba(13, 148, 136, 0.08);
    }
    .job-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .job-company {
        font-size: 1rem;
        font-weight: 600;
        color: #0F766E;
    }

    /* Badges */
    .badge-category-high {
        background-color: #DEF7EC;
        color: #03543F;
        border: 1px solid #BCF0DA;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-category-good {
        background-color: #E1EFFE;
        color: #1E429F;
        border: 1px solid #B4C6FC;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-category-stretch {
        background-color: #FEF08A;
        color: #713F12;
        border: 1px solid #FDE047;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-category-low {
        background-color: #F3F4F6;
        color: #4B5563;
        border: 1px solid #E5E7EB;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }

    .badge-source {
        background: #F1F5F9;
        color: #334155;
        border: 1px solid #CBD5E1;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }
    .badge-workmode {
        background: #F8FAFC;
        color: #475569;
        border: 1px solid #E2E8F0;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .skill-chip-matched {
        display: inline-block;
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        padding: 0.15rem 0.55rem;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 600;
        margin: 0.15rem;
    }
    .skill-chip-missing {
        display: inline-block;
        background-color: #FFFBEB;
        color: #92400E;
        border: 1px solid #FDE68A;
        padding: 0.15rem 0.55rem;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 600;
        margin: 0.15rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
@st.cache_data(show_spinner=False)
def load_candidate_profile():
    path = settings.get_absolute_profile_path()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_database_history():
    try:
        init_db()
        with get_db_session() as session:
            runs = (
                session.query(PipelineRunModel)
                .order_by(PipelineRunModel.started_at.desc())
                .limit(10)
                .all()
            )
            history = []
            for r in runs:
                history.append({
                    "Run ID": r.run_id,
                    "Started At": r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else "",
                    "Discovered": r.jobs_discovered,
                    "Normalized": r.jobs_normalized,
                    "Deduplicated": r.jobs_deduplicated,
                    "Evaluated": r.jobs_matched,
                    "Recommended": r.jobs_recommended,
                    "Status": r.status,
                    "Report File": Path(r.report_path).name if r.report_path else "None"
                })
            return pd.DataFrame(history)
    except Exception as e:
        return pd.DataFrame()


def update_application_status_in_db(canonical_id: str, new_status: str):
    try:
        init_db()
        with get_db_session() as session:
            repo = DatabaseRepository(session)
            repo.update_application_status(
                canonical_id=canonical_id,
                status=ApplicationStatus(new_status)
            )
            return True
    except Exception as e:
        st.error(f"Error updating status: {e}")
        return False


def run_pipeline_orchestration():
    with st.spinner("Launching multi-agent LangGraph pipeline..."):
        app = create_job_discovery_graph()
        final_state = app.invoke({})
        st.session_state["pipeline_results"] = final_state
        st.session_state["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return final_state


# --- Initialize Session State ---
if "pipeline_results" not in st.session_state:
    # Run once automatically or leave empty for user trigger
    # Let's run the pipeline on first load if reports already exist
    today_excel = settings.get_absolute_report_dir() / f"job_matches_{datetime.utcnow().strftime('%Y-%m-%d')}.xlsx"
    if today_excel.exists():
        try:
            app = create_job_discovery_graph()
            st.session_state["pipeline_results"] = app.invoke({})
            st.session_state["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            st.session_state["pipeline_results"] = None
    else:
        st.session_state["pipeline_results"] = None

candidate_data = load_candidate_profile()

# --- Sidebar Configuration ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/artificial-intelligence.png", width=64)
    st.title("AI Job Agent")
    st.caption("Autonomous Discovery & Multi-Layer Matching")
    
    st.divider()

    st.subheader("Candidate Quick View")
    st.markdown(f"**Name:** {candidate_data.get('name', 'Candidate')}")
    st.markdown(f"**Email:** {candidate_data.get('email', 'N/A')}")
    st.markdown(f"**Experience:** ~{candidate_data.get('approx_experience_years', 0)} years")
    
    top_roles = candidate_data.get("target_roles", [])[:3]
    st.markdown(f"**Target Roles:** {', '.join(top_roles)}...")

    st.divider()
    
    st.subheader("Pipeline Controls")
    if st.button("Run Discovery & Matching", type="primary", use_container_width=True):
        try:
            res = run_pipeline_orchestration()
            st.success("Pipeline executed successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error during pipeline execution: {e}")

    if st.session_state.get("last_run_time"):
        st.caption(f"Last executed: {st.session_state['last_run_time']}")

    st.divider()

    # Data Source Notice
    st.info(
        "**Source Mode: Demo / Sample Feed**\n"
        "Active sources: LinkedIn, Indeed, Naukri, Direct Careers. "
        "Pluggable with live ATS / RapidAPI JSearch feeds."
    )


# --- Hero Section ---
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">LangGraph Multi-Agent Architecture</div>
    <div class="hero-title">AI-Powered Job Discovery & Relevance Matcher</div>
    <div class="hero-subtitle">
        Continuously discovering, normalizing, deduplicating, and scoring opportunities 
        across multiple career platforms with explainable AI match justification.
    </div>
</div>
""", unsafe_allow_html=True)


results = st.session_state.get("pipeline_results")

# --- Top Key Performance Metrics ---
if results and results.get("stats"):
    stats = results["stats"]
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Jobs Discovered</div>
            <div class="metric-value">{stats.jobs_discovered}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">After Dedup</div>
            <div class="metric-value">{stats.jobs_deduplicated}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">High Matches (≥85%)</div>
            <div class="metric-value" style="color:#059669;">{stats.high_matches}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Good Matches (≥70%)</div>
            <div class="metric-value" style="color:#2563EB;">{stats.good_matches}</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Recommended</div>
            <div class="metric-value" style="color:#0F766E;">{stats.jobs_recommended}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

# --- Navigation Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Matched Opportunities",
    "Match Analytics",
    "Excel Report & Notification",
    "Candidate Profile",
    "Database & Run History"
])


# ==========================================
# TAB 1: Matched Opportunities
# ==========================================
with tab1:
    if not results or not results.get("ranked_matches"):
        st.info("No pipeline results available yet. Click **'Run Discovery & Matching'** in the sidebar to start!")
    else:
        matches = results["ranked_matches"]

        # Filter & Search Toolbar
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1.5, 1.5, 1.2])

        with filter_col1:
            search_query = st.text_input("Search title, company, or skills:", placeholder="e.g. AI, Python, Analyst...")
        
        with filter_col2:
            category_filter = st.selectbox(
                "Filter by Category:",
                options=["All Categories", "High Match (≥85%)", "Good Match (≥70%)", "Stretch (≥55%)", "Low Match (<55%)"]
            )

        with filter_col3:
            work_mode_filter = st.selectbox(
                "Work Mode:",
                options=["All Modes", "Remote", "Hybrid", "On-site"]
            )

        with filter_col4:
            min_score = st.slider("Min Score:", min_value=0, max_value=100, value=50, step=5)

        # Apply Filtering
        filtered_matches = []
        for m in matches:
            # Score filter
            if m.relevance_score < min_score:
                continue

            # Category filter
            if category_filter == "High Match (≥85%)" and m.category != MatchCategory.HIGH_MATCH:
                continue
            elif category_filter == "Good Match (≥70%)" and m.category != MatchCategory.GOOD_MATCH:
                continue
            elif category_filter == "Stretch (≥55%)" and m.category != MatchCategory.STRETCH:
                continue
            elif category_filter == "Low Match (<55%)" and m.category != MatchCategory.LOW_MATCH:
                continue

            # Work mode filter
            if work_mode_filter != "All Modes" and work_mode_filter.lower() not in m.job.work_mode.lower():
                continue

            # Search query filter
            if search_query:
                q = search_query.lower()
                text_pool = f"{m.job.title} {m.job.company} {' '.join(m.matched_skills)} {m.job.location}".lower()
                if q not in text_pool:
                    continue

            filtered_matches.append(m)

        st.caption(f"Showing **{len(filtered_matches)}** of **{len(matches)}** matched listings")

        # Render Job Cards
        for idx, match in enumerate(filtered_matches):
            cat_val = match.category.value
            cat_badge_class = {
                "HIGH_MATCH": "badge-category-high",
                "GOOD_MATCH": "badge-category-good",
                "STRETCH": "badge-category-stretch",
                "LOW_MATCH": "badge-category-low",
            }.get(cat_val, "badge-category-low")

            cat_display_name = {
                "HIGH_MATCH": "High Match",
                "GOOD_MATCH": "Good Match",
                "STRETCH": "Stretch Opportunity",
                "LOW_MATCH": "Low Relevance"
            }.get(cat_val, cat_val)

            with st.container():
                st.markdown(f"""
                <div class="job-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <span class="{cat_badge_class}">{cat_display_name}</span>
                            <span style="font-size:1.1rem; font-weight:800; color:#0F766E; margin-left:0.6rem;">{match.relevance_score:.1f}% Match</span>
                            <div class="job-title" style="margin-top:0.4rem;">{match.job.title}</div>
                            <div class="job-company">{match.job.company} &nbsp;•&nbsp; <span style="color:#64748B; font-weight:500;">{match.job.location}</span></div>
                        </div>
                        <div style="text-align:right;">
                            <span class="badge-workmode">{match.job.work_mode}</span>
                        </div>
                    </div>
                    <div style="margin-top:0.6rem; color:#475569; font-size:0.9rem;">
                        <strong>Experience:</strong> {match.job.experience_required or 'Flexible'} &nbsp;|&nbsp; 
                        <strong>Salary:</strong> {match.job.salary or 'Disclosed upon interview'} &nbsp;|&nbsp; 
                        <strong>Posted:</strong> {match.job.posted_at.strftime('%Y-%m-%d') if match.job.posted_at else 'Recent'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_details, col_actions = st.columns([3.5, 1.5])

                with col_details:
                    # Why This Matches
                    with st.expander("Why This Matches (Explainable AI Breakdown)", expanded=True):
                        for reason in match.why_matches:
                            st.markdown(f"- {reason}")

                        # Skills breakdown
                        st.markdown("**Matched Candidate Skills:**")
                        matched_html = "".join([f'<span class="skill-chip-matched">{s}</span>' for s in match.matched_skills])
                        st.markdown(matched_html or "<em>None specified in profile</em>", unsafe_allow_html=True)

                        if match.missing_skills:
                            st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
                            st.markdown("**Missing / Learnable Skills:**")
                            missing_html = "".join([f'<span class="skill-chip-missing">! {s}</span>' for s in match.missing_skills])
                            st.markdown(missing_html, unsafe_allow_html=True)

                with col_actions:
                    # Sources
                    st.markdown("**Discovered on:**")
                    sources_html = "".join([f'<span class="badge-source">{s}</span>' for s in match.job.sources])
                    st.markdown(sources_html, unsafe_allow_html=True)

                    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                    if match.job.application_url and match.job.application_url.startswith("http"):
                        st.link_button("Apply Link", match.job.application_url, use_container_width=True)

                    # Application Tracking Selector
                    status_options = [s.value for s in ApplicationStatus]
                    curr_idx = status_options.index(match.application_status.value) if match.application_status.value in status_options else 0
                    
                    selected_status = st.selectbox(
                        "Status Tracker:",
                        options=status_options,
                        index=curr_idx,
                        key=f"status_select_{match.job.canonical_id}_{idx}"
                    )
                    if selected_status != match.application_status.value:
                        if update_application_status_in_db(match.job.canonical_id, selected_status):
                            match.application_status = ApplicationStatus(selected_status)
                            st.toast(f"Status updated to: {selected_status}")

                st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px dashed #E2E8F0;'>", unsafe_allow_html=True)


# ==========================================
# TAB 2: Match Analytics
# ==========================================
with tab2:
    if not results or not results.get("ranked_matches"):
        st.info("Run the pipeline first to generate analytics.")
    else:
        matches = results["ranked_matches"]

        st.subheader("Relevance Scoring & Market Distribution")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### Matches by Category")
            cat_counts = {}
            for m in matches:
                cat_counts[m.category.value] = cat_counts.get(m.category.value, 0) + 1
            df_cat = pd.DataFrame(list(cat_counts.items()), columns=["Category", "Count"])
            st.bar_chart(df_cat.set_index("Category"), color="#0D9488")

        with c2:
            st.markdown("#### Opportunities by Job Source")
            source_counts = {}
            for m in matches:
                for s in m.job.sources:
                    source_counts[s] = source_counts.get(s, 0) + 1
            df_src = pd.DataFrame(list(source_counts.items()), columns=["Source", "Count"])
            st.bar_chart(df_src.set_index("Source"), color="#3B82F6")

        st.divider()

        st.markdown("#### Top Matched Technical Skills Across Listings")
        skill_counts = {}
        for m in matches:
            for s in m.matched_skills:
                skill_counts[s] = skill_counts.get(s, 0) + 1
        
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if sorted_skills:
            df_skills = pd.DataFrame(sorted_skills, columns=["Skill", "Occurrences in Matched Jobs"])
            st.dataframe(df_skills, use_container_width=True, hide_index=True)


# ==========================================
# TAB 3: Excel Report & Notifications
# ==========================================
with tab3:
    st.subheader("Automated Excel Deliverable")
    
    report_path = results.get("report_path") if results else None
    if report_path and Path(report_path).exists():
        path_obj = Path(report_path)
        st.success(f"**Excel report generated successfully:** `{path_obj.name}` ({path_obj.stat().st_size / 1024:.1f} KB)")
        
        with open(path_obj, "rb") as f:
            st.download_button(
                label="Download Full Excel Report (.xlsx)",
                data=f.read(),
                file_name=path_obj.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        
        st.markdown("""
        **Excel Workbook Contents:**
        - **Sheet 1 (Summary)**: High-level KPI metrics, date stamp, breakdown by platform source, and location distributions.
        - **Sheet 2 (Job Matches)**: Fully styled, auto-filtered, color-coded rows with complete role details, matched vs missing skills, and embedded application hyperlinks.
        """)
    else:
        st.info("No Excel report has been generated yet for this session.")

    st.divider()

    st.subheader("Email Notification Preview")
    report_dir = settings.get_absolute_report_dir()
    email_previews = sorted(list(report_dir.glob("email_preview_*.txt")), reverse=True)
    
    if email_previews:
        latest_email_file = email_previews[0]
        with open(latest_email_file, "r", encoding="utf-8") as f:
            email_text = f.read()

        st.markdown(f"**Latest Simulated Email Dispatch:** (`{latest_email_file.name}`)")
        st.code(email_text, language="yaml")
    else:
        st.caption("No email notifications logged yet.")


# ==========================================
# TAB 4: Candidate Profile & Preferences
# ==========================================
with tab4:
    st.subheader("Candidate Resume & Scoring Preferences")
    
    cp_col1, cp_col2 = st.columns(2)
    
    with cp_col1:
        st.markdown("#### Basic Information")
        st.write(f"**Name:** {candidate_data.get('name')}")
        st.write(f"**Email:** {candidate_data.get('email')}")
        st.write(f"**Phone:** {candidate_data.get('phone')}")
        st.write(f"**Target Experience:** {candidate_data.get('experience_preference', {}).get('min_years')} - {candidate_data.get('experience_preference', {}).get('max_years')} yrs (Tolerance: ±{candidate_data.get('experience_preference', {}).get('tolerance_years')} yrs)")
        
        st.markdown("#### Target Roles")
        roles = candidate_data.get("target_roles", [])
        st.write(", ".join(roles))

        st.markdown("#### Preferred Locations & Work Modes")
        st.write(f"**Locations:** {', '.join(candidate_data.get('location_preferences', []))}")
        st.write(f"**Work Modes:** {', '.join(candidate_data.get('work_modes', []))}")

    with cp_col2:
        st.markdown("#### Technical Skill Arsenal (26+ Skills)")
        skills = candidate_data.get("technical_skills", [])
        skills_html = "".join([f'<span class="skill-chip-matched">{s}</span>' for s in skills])
        st.markdown(skills_html, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown("#### Scoring Dimensions & Weights")
        weights = candidate_data.get("scoring_weights", {})
        df_weights = pd.DataFrame(list(weights.items()), columns=["Dimension", "Weight"])
        st.dataframe(df_weights, use_container_width=True, hide_index=True)


# ==========================================
# TAB 5: Database & Run History
# ==========================================
with tab5:
    st.subheader("Database Pipeline Execution History")
    st.caption("Stored persistently in local SQLite (`job_agent.db`) or PostgreSQL")

    df_history = load_database_history()
    if not df_history.empty:
        st.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.info("No prior database runs recorded yet.")
