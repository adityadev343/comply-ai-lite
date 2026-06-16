```markdown
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
```

Create a `.env` file:
```
GROQ_API_KEY=your_actual_key_here
```

```bash
streamlit run app.py
```

---

## ☁️ Deploying on Streamlit Cloud

1. Push your code to GitHub and deploy via [share.streamlit.io](https://share.streamlit.io).
2. Go to **Settings → Secrets** and add:
```toml
GROQ_API_KEY = "your_groq_api_key"
```

> **Note:** Never commit your `.env` file or API keys to GitHub.

---

## 🧪 Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key (required) |
| `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION` | Set to `"python"` to avoid protobuf errors |

---

## 📜 License

MIT License – see the `LICENSE` file for details.

## 🙏 Acknowledgements

[Groq](https://groq.com/) · [Streamlit](https://streamlit.io/) · [LangChain](https://www.langchain.com/) · [Chroma](https://www.trychroma.com/)
```
