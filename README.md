# ⚖️ COMPLY.AI Lite — AI Regulatory Intelligence & Compliance Assurance System

**Built by a Student-Fresher** inspired by the original ARIRAS project.

---

## The Problem

Regulatory compliance has become overwhelmingly complex for businesses.

- Enterprises operate across multiple jurisdictions (India, EU, US, etc.)
- They must comply with overlapping regulations such as **DPDP Act**, **GDPR**, **SEBI**, **RBI**, **SOX**, **CCPA**, and many more
- Keeping up with frequent updates, interpreting legal language, mapping obligations to internal policies, and identifying gaps is time-consuming and expensive
- Most companies cannot afford Big-4 consulting fees for every regulation

**Result:** delayed compliance, high risk exposure, and reactive firefighting instead of proactive governance.

---

## The Solution: COMPLY.AI Lite

**COMPLY.AI Lite** is a **universal, regulation-agnostic** AI system that helps organizations quickly understand, analyze, and comply with **any** regulatory document.

Upload **any regulation PDF** — whether it is the DPDP Act, a SEBI circular, an RBI guideline, GDPR text, SOX requirements, or any other document — and the system instantly becomes an expert on it.

### Core Capabilities

1. **Regulation Q&A**  
   Ask any question about the uploaded regulation and get precise, clause-cited answers.

2. **Gap Detector**  
   Upload your company policy or internal document and receive a detailed gap analysis with severity levels, rationales, and recommended actions.

3. **Policy Builder**  
   Answer a few plain-English questions about your business and get tailored compliance guidance with sample clauses and priority actions.

---

## Why COMPLY.AI Lite Stands Out

- **Truly Regulation-Agnostic:** Works with **any** regulatory PDF, Indian or global
- **Smart DPDP Handling:** Enhanced intelligence for Indian regulations, especially the DPDP Act, including Significant Data Fiduciary classification, children's data, and conditional obligations
- **Improved Accuracy:** Multi-query retrieval, better document chunking, and refined prompts to minimize hallucinations
- **Professional Outputs:** Clean, well-formatted Excel reports ready for internal use or audits
- **Modern & User-Friendly:** Sleek dark UI with interactive metrics and charts
- **Lightweight & Local-First:** Easy to run locally with minimal cost

This project builds on the strong foundation of ARIRAS with cleaner architecture, better retrieval, and more robust handling of complex regulatory nuances.

---

## Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | Streamlit |
| **LLM** | Groq — Llama 3.3 70B |
| **Framework** | LangChain |
| **Vector DB** | ChromaDB |
| **Embeddings** | all-MiniLM-L6-v2 |
| **PDF Parsing** | PyPDF2 + Custom Extractor |
| **Reports** | openpyxl (Styled Excel) |

---

## Architecture

```text
Streamlit UI (Q&A + Gap Analysis + Policy Builder)
↓
Core Engines (RAG, Gap, Builder)
↓
Vector Store (ChromaDB + Smart Chunking)
↓
Groq LLM (Llama 3.3 70B)
```

---

## Project Structure

```bash
comply-ai-lite/
├── app.py
├── core/                  # RAG, Gap, Builder, VectorStore logic
├── utils/                 # Excel export utilities
├── data/uploads/          # Temporary uploaded files
├── testing/               # Sample regulations & policies
├── requirements.txt
└── README.md
```

---

## Quick Start

```bash
git clone <repo-url>
cd comply-ai-lite
pip install -r requirements.txt
```

Add your Groq API key to `.env`, then run:

```bash
streamlit run app.py
```

---

## How to Use

### Tab 1: Regulation Q&A

- Upload any regulation PDF
- Process and index it
- Ask questions such as:
  - “What are the breach notification requirements?”
  - “What are the obligations of a Significant Data Fiduciary?”

### Tab 2: Gap Detector

- Upload a regulation plus your company policy
- Optionally specify classification for DPDP-like regulations
- Get a compliance score and a detailed gap report with Excel download

### Tab 3: Policy Builder

- Describe your business in plain English
- Generate custom policy guidance with sample clauses tailored to your operations

---

## Key Features

- **Universal Compatibility** — Any regulation PDF works
- **Clause-Level Citations** — Always references exact text from the document
- **Actionable Insights** — Not just gaps, but clear recommendations
- **Smart Classification** — Handles conditional obligations, such as Significant Data Fiduciary under DPDP
- **Professional Reports** — Downloadable, well-formatted Excel files
- **Local & Private** — Your documents stay on your machine
