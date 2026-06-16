# ⚖️ COMPLY.AI – Regulatory Intelligence & Compliance Assurance

**COMPLY.AI** is an AI‑powered tool that helps organisations understand complex regulations, assess their current policies, and generate actionable compliance guidance. It uses **Retrieval-Augmented Generation (RAG)** to provide precise answers, gap analyses, and tailored policy recommendations.

---

## ✨ Key Features

- **📖 Regulation Q&A** – Ask any question about your uploaded regulation; the assistant retrieves exact citations from the full document.
- **🔍 Gap Detector** – Upload your company's existing policy; COMPLY.AI maps every obligation and flags what's missing, with severity and recommended actions.
- **📝 Policy Builder** – Answer 5 simple questions about your business; the system generates a custom compliance report with sample clauses and priorities.
- **📊 Interactive Dashboard** – Visualise compliance scores, gap severity, and progress over time.
- **📥 Excel Export** – Download comprehensive reports as styled Excel files.

---

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **LLM**: [Groq](https://groq.com/) (Llama 3.3 70B)
- **Vector Database**: [ChromaDB](https://www.trychroma.com/) with `all‑MiniLM‑L6‑v2` embeddings
- **Document Processing**: `PyPDF2`, `langchain` text splitters
- **Export**: `openpyxl`
- **Language**: Python 3.10

---

## 🚀 Running Locally

```bash
git clone https://github.com/your-username/comply-ai-lite.git
cd comply-ai-lite
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
