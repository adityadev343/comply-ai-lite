import os
import re
import streamlit as st
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

# --- Page config ---
st.set_page_config(
    page_title="COMPLY.AI - Regulatory Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS (only essential) ---
st.markdown("""
<style>
    /* Dark theme */
    .stApp { background-color: #0E1117; }
    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border-left: 6px solid #3B82F6;
    }
    .main-header h1 { color: #FFFFFF; font-weight: 700; font-size: 2.2rem; }
    .main-header p { color: #94A3B8; }
    .badge-success {
        background-color: #064E3B;
        color: #A7F3D0;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    .stButton > button {
        background: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        border: none;
    }
    .stButton > button:hover { background: #1D4ED8; }
    .stButton > button:disabled { background: #475569; }
    .stTabs [data-baseweb="tab"] {
        background: #1E293B;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: #94A3B8;
        border: 1px solid #334155;
    }
    .stTabs [aria-selected="true"] {
        background: #2563EB !important;
        color: white !important;
        border-color: #2563EB;
    }
    .metric-card {
        background: #1E293B;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        border: 1px solid #334155;
        text-align: center;
        border-left: 5px solid #3B82F6;
    }
    .metric-card.gaps { border-left-color: #EF4444; }
    .metric-card.met { border-left-color: #10B981; }
    .metric-label {
        font-size: 0.75rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 2.8rem;
        font-weight: 700;
        color: #F8FAFC;
        line-height: 1.2;
    }
    .status-badge {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 2px 14px;
        border-radius: 20px;
        margin-top: 0.25rem;
    }
    .status-good { background: #10B981; color: #FFFFFF; }
    .status-critical { background: #EF4444; color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

# --- Session state ---
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

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚖️ COMPLY.AI")
    st.caption("AI Regulatory Intelligence System")
    st.markdown("---")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        st.error("⚠️ API missing! Add it to your .env file.")
    else:
        st.success("✅ Assistant is ready!")
    st.markdown("---")
    st.markdown("**📂 System Status**")
    if st.session_state.regulation_text:
        st.markdown(f"<span class='badge-success'>✅ Regulation Loaded</span>", unsafe_allow_html=True)
        st.caption(f"File: {st.session_state.regulation_name}")
    else:
        st.markdown("❌ No Regulation Loaded")
    st.markdown("---")
    st.markdown("**📊 Dashboard**")
    if st.session_state.gap_history:
        latest = st.session_state.gap_history[-1]
        st.metric("Latest Compliance Score", f"{latest['score']}%")
        st.metric("Total Gaps Found", latest.get('gaps', 0))
    else:
        st.caption("Run a gap analysis to see metrics here.")
    st.markdown("---")
    st.caption("Aditya Dev Sen")

# --- Main UI ---
st.markdown("""
<div class="main-header">
    <h1>⚖️ COMPLY.AI</h1>
    <p>AI Regulatory Intelligence & Reporting Assurance System</p>
</div>
""", unsafe_allow_html=True)

# --- Regulation Upload ---
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

st.markdown("---")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📖 1. Regulation Q&A", "🔍 2. Gap Detector", "📝 3. Policy Builder"])

# --- TAB 1: Q&A ---
with tab1:
    st.markdown("### Ask anything about the regulation")
    st.caption("Our assistant reads the **entire** document to answer your question with exact citations.")
    if not st.session_state.regulation_text:
        st.warning("⚠️ Please upload a regulation first.")
    else:
        question = st.text_area("Your question:", placeholder="e.g. What are the breach notification timelines?")
        if st.button("🔎 Get Answer", type="primary"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Analyzing the full document..."):
                    answer = ask_question(st.session_state.regulation_text, question)
                    st.session_state.rag_answer = answer
        if st.session_state.rag_answer:
            st.markdown("#### 📌 Answer:")
            st.markdown(f"<div class='result-box'>{st.session_state.rag_answer}</div>", unsafe_allow_html=True)

# --- TAB 2: GAP DETECTOR ---
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
            
            # ---------- METRIC CARDS ----------
            is_good = score >= 50
            status_text = "✅ Good" if is_good else "⚠️ Critical"
            status_class = "status-good" if is_good else "status-critical"
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
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
                    <div style="font-size:0.75rem;color:#64748B;">Identified</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="metric-card met">
                    <div class="metric-label">✅ Obligations Met</div>
                    <div class="metric-value">{total_met}</div>
                    <div style="font-size:0.75rem;color:#64748B;">Fulfilled</div>
                </div>
                """, unsafe_allow_html=True)
            
            # ---------- CHARTS (Bar + Donut) ----------
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
                    title='🚨 Gap Severity Breakdown',
                    height=220,
                    margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor='#1E293B',
                    plot_bgcolor='#1E293B',
                    font_color='#E2E8F0',
                    xaxis=dict(title='Number of Gaps', gridcolor='#334155'),
                    yaxis=dict(gridcolor='#334155'),
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
                    title='📊 Compliance Status Overview',
                    height=220,
                    margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor='#1E293B',
                    font_color='#E2E8F0',
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True, key="compliance_donut")
            
            # ---------- GAP LIST ----------
            st.markdown("#### 🚨 Identified Gaps (Top 5)")
            for gap in res.get("gaps", [])[:5]:
                sev_color = "🔴" if gap['severity'] == 'high' else "🟡" if gap['severity'] == 'medium' else "🟢"
                st.markdown(f"""
                <div style="background:#1E293B;border:1px solid #334155;border-radius:8px;padding:12px;margin-bottom:8px;color:#E2E8F0;">
                    <b>{sev_color} {gap['obligation']}</b> <span style="color:#94A3B8;font-size:0.8rem;">({gap['severity'].upper()})</span>
                    <p style="margin:4px 0 0 0;font-size:0.9rem;">📌 {gap['what_is_missing']}</p>
                    <p style="margin:2px 0 0 0;font-size:0.85rem;color:#94A3B8;">💡 {gap['recommended_action']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # ---------- EXCEL DOWNLOAD ----------
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

# --- TAB 3: POLICY BUILDER ---
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

st.markdown("---")
st.caption("⚖️ COMPLY.AI — Built to simplify compliance. No hidden costs. Just pure AI.")