import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import re
import streamlit as st
# --- Make Streamlit secrets available as environment variables ---
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

import datetime
import plotly.graph_objects as go
from dotenv import load_dotenv

# --- Suppress logging ---
import logging
import warnings
warnings.filterwarnings("ignore")
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("langchain").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Imports from your project ---
from core.pdf_reader import extract_text_from_pdf
from core.rag_engine import ask_question
from core.gap_engine import run_gap_analysis
from core.builder_engine import generate_policy_guidance
from utils.excel_export import build_gap_excel, build_policy_excel

load_dotenv()

# --- Helper for filenames ---
def sanitize_filename(name: str) -> str:
    if not name:
        return "unknown"
    name = re.sub(r'\.(pdf|txt|docx|doc|xlsx?)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '_', name)
    return name.strip('_')

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="COMPLY.AI - Regulatory Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS — PREMIUM DARK GLASSMORPHISM (Legal/Compliance Theme)
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800;900&display=swap');

/* ── DESIGN TOKENS ─────────────────────────────────────────────────────────── */
:root {
    --bg-void:       #060b17;
    --bg-deep:       #0b1321;
    --navy:          #0f1a2e;
    --navy-mid:      #162b45;
    --blue-accent:   #2563eb;
    --blue-glow:     #3b82f6;
    --gold:          #fbbf24;
    --gold-dim:      rgba(251,191,36,0.35);
    --text-main:     #f1f5f9;
    --text-dim:      #94a3b8;
    --text-ghost:    rgba(241,245,249,0.35);
    --glass:         rgba(15,23,42,0.65);
    --glass-hover:   rgba(30,41,59,0.80);
    --glass-border:  rgba(59,130,246,0.15);
    --glass-border-h:rgba(59,130,246,0.50);
    --shadow-card:   0 24px 60px -20px rgba(0,0,0,0.8);
    --shadow-glow:   0 0 40px -10px rgba(37,99,235,0.30);
}

/* ── GLOBAL RESETS ──────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    color: var(--text-main);
}
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }

/* Background */
.stApp {
    background:
        radial-gradient(ellipse 60% 40% at 10% 5%,  rgba(37,99,235,0.12), transparent),
        radial-gradient(ellipse 50% 35% at 90% 0%,  rgba(59,130,246,0.06), transparent),
        radial-gradient(ellipse 80% 50% at 50% 100%, rgba(6,11,23,0.80),    transparent),
        linear-gradient(180deg, var(--bg-void) 0%, var(--bg-deep) 100%);
    min-height: 100vh;
}

/* Scrollbar */
::-webkit-scrollbar       { width: 8px; }
::-webkit-scrollbar-track { background: var(--bg-void); }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg, var(--blue-accent), var(--navy)); border-radius: 8px; }

/* ── HERO HEADER ────────────────────────────────────────────────────────────── */
.hero-wrap {
    position: relative;
    overflow: hidden;
    border-radius: 28px;
    padding: 48px 40px 40px;
    margin-bottom: 32px;
    background: linear-gradient(160deg, rgba(15,23,42,0.90) 0%, rgba(6,11,23,0.95) 100%);
    border: 1px solid var(--glass-border);
    box-shadow: var(--shadow-card), var(--shadow-glow);
}
@media (max-width: 768px) {
    .hero-wrap { padding: 32px 20px 28px; }
    .hero-title { font-size: 32px !important; }
    .hero-sub   { font-size: 15px !important; }
}

/* Floating legal icons */
.float-layer {
    position: absolute; inset: 0; overflow: hidden; pointer-events: none; z-index:1;
}
.floating-icon {
    position: absolute;
    filter: drop-shadow(0 0 12px rgba(59,130,246,0.25));
    animation-name: floaty; animation-timing-function: ease-in-out; animation-iteration-count: infinite;
    opacity: 0.20;
}
.floating-icon:nth-child(odd) { animation-duration: 9s; }
.floating-icon:nth-child(even) { animation-duration: 13s; }
@keyframes floaty {
    0%   { transform: translateY(0px) rotate(0deg); }
    50%  { transform: translateY(-28px) rotate(12deg); }
    100% { transform: translateY(0px) rotate(0deg); }
}

/* Hero content */
.hero-content { position: relative; z-index: 2; }
.hero-eyebrow {
    display: inline-block; padding: 6px 18px; border-radius: 999px;
    background: rgba(59,130,246,0.08); border: 1px solid var(--glass-border);
    color: var(--blue-glow); font-size: 12px; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 18px;
}
.hero-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 48px; font-weight: 900; line-height: 1.05; margin: 0 0 12px;
    background: linear-gradient(100deg, #ffffff 0%, #93c5fd 40%, var(--blue-glow) 70%, var(--gold) 100%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 30px rgba(59,130,246,0.15));
}
.hero-desc {
    font-size: 15px; color: var(--text-dim);
    max-width: 640px; line-height: 1.7;
}
.hero-pill {
    display: inline-block; margin-top: 18px; padding: 10px 28px;
    border-radius: 14px; font-weight: 700; font-size: 14px;
    background: linear-gradient(120deg, var(--blue-accent), var(--blue-glow));
    color: #ffffff; box-shadow: 0 12px 32px -8px rgba(37,99,235,0.60);
    letter-spacing: 0.02em;
}

/* ── SECTION HEADERS ────────────────────────────────────────────────────────── */
.sec-head { margin: 40px 0 20px; }
.sec-tag  {
    color: var(--blue-glow); font-size: 11px; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
}
.sec-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 26px; font-weight: 800; margin: 6px 0 2px; color: var(--text-main);
}
.sec-desc { color: var(--text-dim); font-size: 14px; line-height: 1.6; }

/* ── GLASS CARDS ────────────────────────────────────────────────────────────── */
.glass-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    padding: 24px 22px;
    box-shadow: var(--shadow-card);
    transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}
.glass-card:hover {
    transform: translateY(-4px);
    border-color: var(--glass-border-h);
    box-shadow: 0 28px 60px -20px rgba(37,99,235,0.30), var(--shadow-card);
}

/* ── METRIC CARDS ──────────────────────────────────────────────────────────────── */
.metric-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 18px;
    padding: 24px 16px;
    text-align: center;
    backdrop-filter: blur(12px);
    transition: transform 0.30s ease, box-shadow 0.30s ease, border-color 0.30s ease;
    border-left: 6px solid var(--blue-accent);
}
.metric-card:hover {
    transform: translateY(-6px);
    border-color: var(--glass-border-h);
    box-shadow: 0 20px 48px -18px rgba(37,99,235,0.40);
}
.metric-card.gaps  { border-left-color: #ef4444; }
.metric-card.met   { border-left-color: #10b981; }
.metric-card.score { border-left-color: var(--gold); }
.metric-label {
    color: var(--text-dim); font-size: 11px; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 6px;
}
.metric-value {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 2.6rem; font-weight: 900; line-height: 1.1;
    background: linear-gradient(100deg, #ffffff, var(--blue-glow));
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-sub {
    color: var(--text-dim); font-size: 12px; margin-top: 4px;
}
.status-badge {
    display: inline-block; padding: 4px 18px; border-radius: 999px;
    font-size: 12px; font-weight: 700; letter-spacing: 0.04em;
    margin-top: 6px;
}
.status-good     { background: rgba(16,185,129,0.15); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.30); }
.status-critical { background: rgba(239,68,68,0.15);   color: #fca5a5; border: 1px solid rgba(239,68,68,0.30); }

/* ── BADGE / CHIP ────────────────────────────────────────────────────────────── */
.badge-success {
    background-color: #064E3B; color: #A7F3D0;
    padding: 4px 12px; border-radius: 20px; font-size: 0.75rem;
}

/* ── TABS (pill style) ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--glass) !important;
    border-radius: 14px !important;
    border: 1px solid var(--glass-border) !important;
    padding: 6px !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-dim) !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    padding: 8px 20px !important;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: rgba(59,130,246,0.15) !important;
    color: var(--blue-glow) !important;
    border: 1px solid rgba(59,130,246,0.30) !important;
}

/* ── FORM CONTROLS ────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 20px !important;
    padding: 28px 26px !important;
    backdrop-filter: blur(14px) !important;
}
.stSelectbox label, .stTextInput label, .stTextArea label, .stRadio label {
    color: var(--text-dim) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
.stTextInput input, .stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 12px !important;
    color: var(--text-main) !important;
}
.stButton > button, .stFormSubmitButton button {
    background: linear-gradient(120deg, var(--blue-accent), var(--blue-glow)) !important;
    color: white !important; font-weight: 700 !important; font-size: 14px !important;
    border: none !important; border-radius: 12px !important; padding: 10px 0 !important;
    box-shadow: 0 12px 34px -8px rgba(37,99,235,0.55) !important;
    transition: transform 0.24s ease, box-shadow 0.24s ease !important;
    letter-spacing: 0.02em !important;
}
.stButton > button:hover, .stFormSubmitButton button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 18px 40px -8px rgba(37,99,235,0.75) !important;
}
.stButton > button:disabled {
    background: #475569 !important;
    box-shadow: none !important;
}

/* ── GAP LIST ITEMS ────────────────────────────────────────────────────────── */
.gap-item {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}
.gap-item:hover { border-color: var(--glass-border-h); }
.gap-sev-high   { border-left: 4px solid #ef4444; }
.gap-sev-medium { border-left: 4px solid #f59e0b; }
.gap-sev-low    { border-left: 4px solid #10b981; }

/* ── RESPONSIVE TWEAKS ────────────────────────────────────────────────────── */
@media (max-width: 640px) {
    .hero-title { font-size: 28px !important; }
    .metric-value { font-size: 2rem !important; }
    .stTabs [data-baseweb="tab"] { font-size: 11px !important; padding: 6px 12px !important; }
}

/* ── FOOTER ─────────────────────────────────────────────────────────────────── */
.app-footer {
    text-align: center; color: var(--text-dim);
    font-size: 12px; padding: 36px 0 12px; opacity: 0.5;
    letter-spacing: 0.04em;
}
.fancy-divider {
    border: none; height: 1px;
    background: linear-gradient(90deg, transparent, var(--glass-border), transparent);
    margin: 40px 0;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE (unchanged)
# =============================================================================
if 'regulation_text' not in st.session_state:
    st.session_state.regulation_text = None
    st.session_state.regulation_name = None
if 'gap_result' not in st.session_state:
    st.session_state.gap_result = None
if 'gap_history' not in st.session_state:
    st.session_state.gap_history = []
if 'policy_guidance' not in st.session_state:
    st.session_state.policy_guidance = None
if 'builder_excel' not in st.session_state:
    st.session_state.builder_excel = None
if 'builder_company_name' not in st.session_state:
    st.session_state.builder_company_name = None
if 'rag_answer' not in st.session_state:
    st.session_state.rag_answer = None
if 'indexing_in_progress' not in st.session_state:
    st.session_state.indexing_in_progress = False
if 'policy_file_name' not in st.session_state:
    st.session_state.policy_file_name = None

# =============================================================================
# SIDEBAR (refined)
# =============================================================================
with st.sidebar:
    st.markdown("### ⚖️ COMPLY.AI")
    st.caption("Regulatory Intelligence System")
    st.markdown("---")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        st.error("⚠️ API missing! Add to .env")
    else:
        st.success("✅ Assistant ready")
    st.markdown("---")
    st.markdown("**📂 System Status**")
    if st.session_state.regulation_text:
        st.markdown(f"<span class='badge-success'>✅ Regulation Loaded</span>", unsafe_allow_html=True)
        st.caption(f"File: {st.session_state.regulation_name}")
    else:
        st.markdown("❌ No Regulation Loaded")
    st.markdown("---")
    st.markdown("**📊 Quick Stats**")
    if st.session_state.gap_history:
        latest = st.session_state.gap_history[-1]
        st.metric("Latest Compliance", f"{latest['score']}%")
        st.metric("Total Gaps", latest.get('gaps', 0))
    else:
        st.caption("Run a gap analysis to see stats.")
    st.markdown("---")
    st.caption("Aditya Dev Sen")

# =============================================================================
# MAIN UI — HERO HEADER
# =============================================================================
# Floating legal icons
float_html = """
<div class="float-layer">
    <span class="floating-icon" style="left:5%;top:12%;font-size:48px;">⚖️</span>
    <span class="floating-icon" style="left:88%;top:8%;font-size:56px;">📜</span>
    <span class="floating-icon" style="left:12%;top:72%;font-size:42px;">🏛️</span>
    <span class="floating-icon" style="left:78%;top:74%;font-size:46px;">📋</span>
    <span class="floating-icon" style="left:45%;top:4%;font-size:36px;">🔍</span>
    <span class="floating-icon" style="left:62%;top:85%;font-size:40px;">📊</span>
</div>
"""
st.markdown(f"""
<div class="hero-wrap">
    {float_html}
    <div class="hero-content">
        <span class="hero-eyebrow">⚖️ AI-Powered Regulatory Intelligence</span>
        <div class="hero-title">COMPLY.AI</div>
        <div class="hero-desc">
            Upload any regulation — from GDPR and DPDP to SEBI, RBI, SOX, or CCPA.
            Ask questions, detect gaps, and build policy guidance with
            <strong>clause-level citations</strong>.
        </div>
        <span class="hero-pill">🚀 Start with a Regulation</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# REGULATION UPLOAD (unchanged logic, only layout)
# =============================================================================
with st.container():
    st.markdown("### 📄 Upload Your Regulation")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload any regulation (GDPR, SEBI, RBI, SOX, etc.)", type=["pdf"], label_visibility="collapsed")
    with col2:
        if uploaded_file:
            disabled = st.session_state.indexing_in_progress
            if st.button("🚀 Process & Index", use_container_width=True, disabled=disabled):
                st.session_state.indexing_in_progress = True
                progress_bar = st.progress(0, text="Starting...")
                status_text = st.empty()
                try:
                    status_text.info("💾 Saving file...")
                    progress_bar.progress(10, text="Saving file...")
                    os.makedirs("data/uploads", exist_ok=True)
                    file_path = f"data/uploads/{uploaded_file.name}"
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    status_text.info("📄 Extracting text from PDF...")
                    progress_bar.progress(30, text="Extracting text...")
                    text = extract_text_from_pdf(uploaded_file)
                    st.session_state.regulation_text = text
                    st.session_state.regulation_name = uploaded_file.name
                    st.session_state.regulation_file_path = file_path

                    status_text.info("🧠 Building vector index...")
                    progress_bar.progress(70, text="Building vector index...")
                    from core.vectorstore import get_retriever
                    get_retriever(file_path)

                    status_text.success("✅ Indexing complete!")
                    progress_bar.progress(100, text="Done!")
                    st.success(f"✅ Successfully loaded and indexed {uploaded_file.name} ({len(text)} characters)")
                except Exception as e:
                    status_text.error(f"❌ Error: {e}")
                    progress_bar.empty()
                    st.error(f"Error: {e}")
                finally:
                    st.session_state.indexing_in_progress = False
                    st.rerun()
    if st.session_state.regulation_text:
        st.info(f"🧠 **Regulation loaded:** {st.session_state.regulation_name} (Full text stored)")

st.markdown('<hr class="fancy-divider">', unsafe_allow_html=True)

# =============================================================================
# TABS (with enhanced styling)
# =============================================================================
tab1, tab2, tab3 = st.tabs(["📖 1. Regulation Q&A", "🔍 2. Gap Detector", "📝 3. Policy Builder"])

# =============================================================================
# TAB 1: Q&A (logic unchanged)
# =============================================================================
with tab1:
    st.markdown("### Ask anything about the regulation")
    st.caption("Our assistant reads the **entire** document to answer your question with exact citations.")
    if not st.session_state.regulation_text:
        st.warning("⚠️ Please upload a regulation first.")
    else:
        question = st.text_area("Your question:", placeholder="e.g. What are the breach notification timelines?")
        if st.button("🔎 Get Answer", type="primary", use_container_width=False):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Analyzing the full document..."):
                    answer = ask_question(st.session_state.regulation_text, question)
                    st.session_state.rag_answer = answer
        if st.session_state.rag_answer:
            st.markdown("#### 📌 Answer:")
            st.markdown(f"<div class='glass-card' style='border-left:4px solid #3b82f6;'>{st.session_state.rag_answer}</div>", unsafe_allow_html=True)

# =============================================================================
# TAB 2: GAP DETECTOR (logic unchanged, UI enhanced)
# =============================================================================
with tab2:
    st.markdown("### 🔍 Check your policy against the regulation")
    st.caption("Upload your company's existing policy. COMPLY.AI maps every obligation and flags what's missing.")

    if not st.session_state.regulation_text:
        st.warning("⚠️ Please upload a regulation first.")
    else:
        policy_file = st.file_uploader("Upload your Company Policy (PDF or TXT)", type=["pdf", "txt"])
        classification = st.radio(
            "Does your company fall under any special category defined in the uploaded regulation?",
            options=["No", "Yes", "Not specified"],
            index=0,
            help="E.g., 'Significant Data Fiduciary', 'Large Platform', etc."
        )
        if policy_file:
            if st.button("⚡ Run Gap Analysis", type="primary"):
                with st.spinner("Reading your policy and comparing against the regulation..."):
                    result = run_gap_analysis(
                        st.session_state.regulation_text,
                        policy_file,
                        company_classification=classification
                    )
                    st.session_state.gap_result = result
                    st.session_state.policy_file_name = policy_file.name
                    st.session_state.gap_history.append({
                        "score": result.get("compliance_score", 0),
                        "gaps": len(result.get("gaps", [])),
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    })
                    st.success("Analysis Complete!")

        if st.session_state.gap_result:
            res = st.session_state.gap_result
            score = res.get("compliance_score", 0)
            total_gaps = len(res.get("gaps", []))
            total_met = len(res.get("met", []))

            # ---------- METRIC CARDS (upgraded) ----------
            is_good = score >= 50
            status_text = "✅ Good" if is_good else "⚠️ Critical"
            status_class = "status-good" if is_good else "status-critical"

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card score">
                    <div class="metric-label">📊 Compliance Score</div>
                    <div class="metric-value">{score}%</div>
                    <div class="status-badge {status_class}">{status_text}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card gaps">
                    <div class="metric-label">🚨 Total Gaps</div>
                    <div class="metric-value">{total_gaps}</div>
                    <div class="metric-sub">Identified</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="metric-card met">
                    <div class="metric-label">✅ Obligations Met</div>
                    <div class="metric-value">{total_met}</div>
                    <div class="metric-sub">Fulfilled</div>
                </div>
                """, unsafe_allow_html=True)

            # ---------- CHARTS (unchanged but now inside glass cards) ----------
            gaps = res.get("gaps", [])
            high = sum(1 for g in gaps if g.get('severity', '').lower() == 'high')
            medium = sum(1 for g in gaps if g.get('severity', '').lower() == 'medium')
            low = sum(1 for g in gaps if g.get('severity', '').lower() == 'low')

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                fig1 = go.Figure(go.Bar(
                    x=[high, medium, low],
                    y=['High', 'Medium', 'Low'],
                    orientation='h',
                    marker_color=['#EF4444', '#F59E0B', '#10B981'],
                    text=[high, medium, low],
                    textposition='outside',
                    hovertemplate='Severity: %{y}<br>Count: %{x}<extra></extra>'
                ))
                fig1.update_layout(
                    title='🚨 Gap Severity',
                    height=220,
                    margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#E2E8F0',
                    xaxis=dict(title='Number of Gaps', gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    showlegend=False
                )
                st.plotly_chart(fig1, use_container_width=True, key="severity_bar")

            with chart_col2:
                fig2 = go.Figure(go.Pie(
                    labels=['✅ Met', '❌ Gaps'],
                    values=[total_met, total_gaps],
                    hole=0.5,
                    marker_colors=['#3B82F6', '#EF4444'],
                    textinfo='label+percent',
                    hoverinfo='label+value+percent'
                ))
                fig2.update_layout(
                    title='📊 Compliance Status',
                    height=220,
                    margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#E2E8F0',
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True, key="compliance_donut")

            # ---------- GAP LIST (enhanced with severity classes) ----------
            st.markdown("#### 🚨 Identified Gaps")
            for gap in res.get("gaps", []):
                sev = gap['severity'].lower()
                sev_class = f"gap-sev-{sev}"
                sev_icon = "🔴" if sev == 'high' else "🟡" if sev == 'medium' else "🟢"
                st.markdown(f"""
                <div class="gap-item {sev_class}">
                    <b>{sev_icon} {gap['obligation']}</b>
                    <span style="color:#94A3B8;font-size:0.8rem;margin-left:8px;">({gap['severity'].upper()})</span>
                    <p style="margin:6px 0 0 0;font-size:0.9rem;">📌 {gap['what_is_missing']}</p>
                    <p style="margin:4px 0 0 0;font-size:0.85rem;color:#94A3B8;">💡 {gap['recommended_action']}</p>
                </div>
                """, unsafe_allow_html=True)

            # ---------- EXCEL DOWNLOAD (unchanged) ----------
            excel_data = build_gap_excel(res, st.session_state.policy_file_name or "Policy")
            safe_reg = sanitize_filename(st.session_state.regulation_name)
            safe_policy = sanitize_filename(st.session_state.policy_file_name or "Policy")
            file_name = f"Gap_Analysis_{safe_reg}_vs_{safe_policy}.xlsx"
            st.download_button(
                label="📥 Download Full Gap Report (Excel)",
                data=excel_data,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# =============================================================================
# TAB 3: POLICY BUILDER (logic unchanged, UI enhanced)
# =============================================================================
with tab3:
    st.markdown("### 📝 Build a Custom Policy Guidance Report")
    st.caption("Answer 5 questions. COMPLY.AI generates a tailored compliance document with sample clauses.")
    if not st.session_state.regulation_text:
        st.warning("⚠️ Please upload a regulation first.")
    else:
        with st.form("builder_form"):
            st.markdown("#### 🏢 About Your Business")
            name = st.text_input("1. Company Name *", placeholder="e.g. Finova Technologies")
            desc = st.text_area("2. What does your company do? *", placeholder="We provide digital lending solutions to MSMEs...")
            flows = st.text_area("3. What information flows through your business?", placeholder="Customer KYC data, transaction histories...")
            stakeholders = st.text_area("4. Who are your key stakeholders?", placeholder="Customers, RBI, Banking partners, Employees...")
            concerns = st.text_area("5. What compliance areas are you unsure about?", placeholder="Data retention policies, consent mechanisms...")
            builder_classification = st.radio(
                "Does your company fall under any special category defined in the uploaded regulation?",
                options=["No", "Yes", "Not specified"],
                index=0,
                help="E.g., 'Significant Data Fiduciary', 'Large Platform', etc."
            )
            submitted = st.form_submit_button("🚀 Generate My Policy Guidance", use_container_width=True)
            if submitted:
                if not name or not desc:
                    st.error("Please fill in the Company Name and Description.")
                else:
                    with st.spinner("Analyzing your business against the regulation..."):
                        company_data = {
                            "name": name,
                            "description": desc,
                            "information_flows": flows,
                            "stakeholders": stakeholders,
                            "concerns": concerns,
                            "existing_policies": "Not specified",
                            "classification": builder_classification
                        }
                        guidance = generate_policy_guidance(st.session_state.regulation_text, company_data)
                        st.session_state.policy_guidance = guidance
                        st.session_state.builder_excel = build_policy_excel(guidance, name)
                        st.session_state.builder_company_name = name
                        st.success("Guidance Generated!")

        if st.session_state.policy_guidance:
            g = st.session_state.policy_guidance
            st.markdown(f"#### 📊 Readiness Score: **{g.get('readiness_score', 0)}%**")
            st.progress(g.get('readiness_score', 0)/100)
            st.markdown(f"**Summary:** {g.get('summary', '')}")
            st.markdown("#### 📋 Your Custom Policy Sections")
            for sec in g.get("sections", []):
                with st.expander(f"📌 {sec.get('section_name', 'Section')}"):
                    st.markdown(f"**What to include:** {sec.get('what_to_include', '')}")
                    st.markdown(f"**Sample Clause:**\n> {sec.get('sample_clause', '')}")
                    st.markdown(f"*{sec.get('why_it_matters', '')}*  |  Ref: {sec.get('regulation_reference', '')}")
            safe_company = sanitize_filename(st.session_state.builder_company_name or "Company")
            safe_reg = sanitize_filename(st.session_state.regulation_name)
            file_name = f"Policy_Guidance_{safe_company}_{safe_reg}.xlsx"
            st.download_button(
                label="📥 Download Policy Guidance (Excel)",
                data=st.session_state.builder_excel,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("""
<hr class="fancy-divider">
<div class="app-footer">
    ⚖️ COMPLY.AI — Built to simplify compliance. No hidden costs. Just pure AI.
</div>
""", unsafe_allow_html=True)
