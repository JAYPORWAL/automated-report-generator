import json
import os

import streamlit as st
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

from src.config import config_error, settings
from src.constants import LENGTHS, SUPPORTED_GEMINI_MODELS, SUPPORTED_REPORT_TONES
from src.services.gemini_service import check_service_health
from src.utils.validators import ValidationError
from src.workflow.report_workflow import ReportWorkflow

# Set Streamlit Page Config
st.set_page_config(
    page_title="Automated Report Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
if config_error:
    st.error(f"❌ Configuration Error: {config_error}")
    st.stop()

# Premium UI CSS injection
st.markdown(
    """
<style>
    .reportview-container {
        background-color: #F8FAFC;
    }
    .stButton>button {
        background-color: #0F172A;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #3B82F6;
        color: white;
        transform: translateY(-2px);
    }
    .status-card {
        padding: 1rem;
        border-radius: 8px;
        background-color: white;
        border-left: 5px solid #3B82F6;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Cache health status check for resources
@st.cache_resource
def get_system_health():
    return check_service_health()


# Initialize session states
if "events" not in st.session_state:
    st.session_state.events = []
if "results" not in st.session_state:
    st.session_state.results = None
if "error" not in st.session_state:
    st.session_state.error = None

# Sidebar Content
st.sidebar.title("🛠️ Configurations")

# Gemini Key Input (override environment if provided)
gemini_key_input = st.sidebar.text_input(
    "Gemini API Key",
    value=os.environ.get("GEMINI_API_KEY", ""),
    type="password",
    help="Provided API key overrides default .env settings.",
)

tavily_key_input = st.sidebar.text_input(
    "Tavily API Key (Optional)",
    value=os.environ.get("TAVILY_API_KEY", ""),
    type="password",
    help="Enables advanced Tavily search. Falls back to DuckDuckGo if empty.",
)

st.sidebar.markdown("---")

# Settings Selectors
model_selection = st.sidebar.selectbox("Gemini Model", SUPPORTED_GEMINI_MODELS, index=0)
tone_selection = st.sidebar.selectbox("Report Tone", SUPPORTED_REPORT_TONES, index=0)
length_selection = st.sidebar.selectbox("Report Length", LENGTHS, index=1)
slide_count = st.sidebar.slider("Number of Presentation Slides", min_value=5, max_value=15, value=8)
enable_research = st.sidebar.checkbox("Enable Web Research", value=True)

st.sidebar.markdown("---")

# System Status Check (Dynamic indicator)
health_data = get_system_health()
api_configured = bool(gemini_key_input or settings.gemini_api_key)

if api_configured:
    st.sidebar.success("🟢 API Status: Configured")
else:
    st.sidebar.error("🔴 API Status: Gemini Key Required")

# App Header
st.title("📊 Automated Report Generator")
st.markdown(
    "Compose comprehensive, fact-checked, publication-ready research reports "
    "and slide decks using a cooperative multi-agent team."
)

# Disclaimer/Notice
st.info(
    "⚠️ **Disclaimer**: AI-generated content is prone to hallucinations. "
    "Please review and verify all statements before external publication."
)

# Input Panel
with st.container():
    col1, col2 = st.columns([2, 1])
    with col1:
        topic_input = st.text_input(
            "Research Topic",
            placeholder="e.g., The state of fusion energy technology in 2026",
            max_chars=500,
        )
        user_context = st.text_area(
            "User Context / Supplied Information (Optional)",
            placeholder="Add specific documents, reports, or starting facts the agents must consider...",
            height=120,
        )
    with col2:
        target_audience = st.text_input(
            "Target Audience (Optional)",
            placeholder="e.g., Executive Board, Engineering Team, General Public",
        )
        report_requirements = st.text_area(
            "Special Report Requirements (Optional)",
            placeholder="e.g., Include timeline, focus on cost efficiency, list key competitors...",
            height=120,
        )

# Control Buttons
btn_col1, btn_col2, _ = st.columns([1, 1, 3])
with btn_col1:
    generate_clicked = st.button("🚀 Generate Complete Report", use_container_width=True)
with btn_col2:
    if st.button("🧹 Clear Session", use_container_width=True):
        st.session_state.events = []
        st.session_state.results = None
        st.session_state.error = None
        st.rerun()

# Generation Execution
if generate_clicked:
    st.session_state.error = None
    st.session_state.results = None
    st.session_state.events = ["Starting pipeline initialization..."]

    if not topic_input.strip():
        st.session_state.error = "Please enter a valid research topic."
    elif not gemini_key_input.strip() and not settings.gemini_api_key:
        st.session_state.error = "Gemini API key is required. Check sidebar or .env."
    else:
        # Create pipeline progress placeholder
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        try:
            # Instantiate workflow
            workflow = ReportWorkflow(
                gemini_api_key=gemini_key_input or settings.gemini_api_key,
                tavily_api_key=tavily_key_input or settings.tavily_api_key,
            )

            # Step map for progress tracking
            step_progress = {
                "research": 0.20,
                "writing": 0.45,
                "reviewing": 0.70,
                "presentation": 0.85,
                "export": 0.95,
                "complete": 1.0,
            }

            # Run pipeline
            for progress_update in workflow.execute(
                topic=topic_input,
                tone=tone_selection,
                length=length_selection,
                slide_count=slide_count,
                enable_research=enable_research,
                user_context=user_context,
                target_audience=target_audience,
                report_requirements=report_requirements,
                model_selection=model_selection,
            ):
                step = progress_update["step"]
                msg = progress_update["message"]

                # Update progress bar
                progress_val = step_progress.get(step, 0.5)
                progress_bar.progress(progress_val)
                status_text.text(msg)

                # Append sanitized status logs
                st.session_state.events.append(f"[{step.upper()}] {msg}")

                if step == "complete":
                    st.session_state.results = progress_update["results"]

            st.success("🎉 Pipeline executed successfully! Review the output in the tabs below.")

        except ValidationError as val_err:
            st.session_state.error = str(val_err)
        except Exception as err:
            st.session_state.error = f"An unexpected pipeline error occurred: {str(err)}"
            st.session_state.events.append(f"[ERROR] Pipeline halted: {str(err)}")

# Error Banner
if st.session_state.error:
    st.error(f"❌ Error: {st.session_state.error}")

st.markdown("---")

# Tabs Layout
tab_notes, tab_draft, tab_final, tab_feedback, tab_presentation, tab_logs = st.tabs(
    [
        "🔍 Research Notes",
        "📝 Draft Report",
        "⭐ Final Reviewed Report",
        "📈 Review Feedback",
        "🖥️ Presentation Slides",
        "⚙️ System Event Logs",
    ]
)

# Populate Tabs
# 1. Research Notes
with tab_notes:
    if st.session_state.results:
        notes_md = st.session_state.results["research_notes_md"]
        st.markdown(notes_md)
        # Download
        st.download_button(
            label="Download Research Notes (MD)",
            data=notes_md,
            file_name="research_notes.md",
            mime="text/markdown",
        )
    else:
        st.info("No research notes generated. Start by entering a topic above.")

# 2. Draft Report
with tab_draft:
    if st.session_state.results:
        st.markdown(st.session_state.results["draft_report"])
    else:
        st.info("Draft report is currently empty. Run the pipeline to populate.")

# 3. Final Reviewed Report
with tab_final:
    if st.session_state.results:
        final_report = st.session_state.results["final_report"]
        export_paths = st.session_state.results["export_paths"]

        st.markdown(final_report)

        # Download section
        st.markdown("### 📥 Download Report")
        dl_col1, dl_col2, dl_col3 = st.columns(3)

        with dl_col1:
            st.download_button(
                label="Download Markdown (.md)",
                data=final_report,
                file_name="final_report.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with dl_col2:
            try:
                with open(export_paths["report_txt"], "r", encoding="utf-8") as f:
                    txt_data = f.read()
                st.download_button(
                    label="Download Plain Text (.txt)",
                    data=txt_data,
                    file_name="final_report.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            except Exception:
                st.error("Text file unavailable.")

        with dl_col3:
            try:
                with open(export_paths["report_pdf"], "rb") as f:
                    pdf_data = f.read()
                st.download_button(
                    label="Download PDF (.pdf)",
                    data=pdf_data,
                    file_name="final_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception:
                st.error("PDF file unavailable.")
    else:
        st.info("Final report is currently empty. Run the pipeline to populate.")

# 4. Review Feedback
with tab_feedback:
    if st.session_state.results:
        fb = st.session_state.results["review_summary"]
        export_paths = st.session_state.results["export_paths"]

        # Display Score Meter
        score = fb["quality_score"]
        col_m1, col_m2 = st.columns([1, 3])
        with col_m1:
            st.markdown(
                f'<div class="status-card"><div class="metric-label">Quality Score</div>'
                f'<div class="metric-value">{score}/100</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("### Issues Found & Resolved")
        for issue in fb.get("issues_found", []):
            st.markdown(f"- ⚠️ {issue}")

        st.markdown("### Improvements Made")
        for improvement in fb.get("improvements_made", []):
            st.markdown(f"- ✅ {improvement}")

        st.markdown("### Future Suggestions")
        for suggestion in fb.get("suggestions", []):
            st.markdown(f"- 💡 {suggestion}")

        # Download JSON
        fb_json = json.dumps(fb, indent=2)
        st.download_button(
            label="Download Feedback (JSON)",
            data=fb_json,
            file_name="review_feedback.json",
            mime="application/json",
        )
    else:
        st.info("Review feedback is empty. Run the pipeline to populate.")

# 5. Presentation
with tab_presentation:
    if st.session_state.results:
        pres = st.session_state.results["presentation"]
        export_paths = st.session_state.results["export_paths"]

        st.markdown(f"## Slide Summary: {pres.title}")
        st.markdown(f"*{pres.subtitle}*")

        # Display slides
        for idx, slide in enumerate(pres.slides, 1):
            with st.expander(f"Slide {idx}: {slide.title}"):
                for b in slide.bullets:
                    st.markdown(f"- {b}")
                st.markdown("---")
                st.markdown(f"**Speaker Notes:**\n{slide.speaker_notes}")

        # Downloads
        st.markdown("### 📥 Download Presentation")
        pres_col1, pres_col2 = st.columns(2)
        with pres_col1:
            try:
                with open(export_paths["presentation_pptx"], "rb") as f:
                    pptx_data = f.read()
                st.download_button(
                    label="Download Presentation (.pptx)",
                    data=pptx_data,
                    file_name="presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
            except Exception:
                st.error("PPTX file unavailable.")
        with pres_col2:
            try:
                with open(export_paths["speaker_notes_md"], "r", encoding="utf-8") as f:
                    notes_txt = f.read()
                st.download_button(
                    label="Download Speaker Notes (MD)",
                    data=notes_txt,
                    file_name="speaker_notes.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            except Exception:
                st.error("Notes file unavailable.")
    else:
        st.info("Presentation is empty. Run the pipeline to populate.")

# 6. System Logs
with tab_logs:
    st.markdown("### Pipeline Event History")
    if st.session_state.events:
        for event in st.session_state.events:
            st.text(event)
    else:
        st.info("System logs are empty. Execute the pipeline to log activities.")
