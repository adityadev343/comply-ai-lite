# Evaluation Pipeline - COMPLY.AI RAG System

This folder contains the complete evaluation framework used to measure the performance of the **COMPLY.AI** RAG pipeline against the **Digital Personal Data Protection Act, 2023**.

## Purpose

The evaluation suite assesses how well the RAG system (retrieval + generation) answers regulatory questions by computing key metrics:

- **Retrieval Quality**: Context Precision, Recall, and Relevancy
- **Generation Quality**: Faithfulness (no hallucinations), Answer Relevancy
- **Numeric Accuracy**: Exact match of penalties, section numbers, etc.

## Files Overview

| File | Description |
|---|---|
| `evaluation_test_dataset.csv` | Test questions + ground truth answers (50 questions) |
| `step1_generate_responses.py` | Runs the RAG pipeline on all questions and saves raw outputs |
| `step2_run_evaluation.py` | Uses LLM-as-a-Judge to score answers and computes metrics |
| `rag_pipeline.py` | Core RAG logic (retrieval + generation) used in evaluation |
| `numeric_match.py` | Custom exact numeric matching (supports Indian numbering: crore, lakh, etc.) |
| `rag_raw_outputs.json` | Raw outputs from Step 1 (contexts + answers) |
| `evaluation_scored.json` | Full scored results with all metrics |
| `evaluation_detailed.csv` | Detailed per-question results |
| `evaluation_report.xlsx` | Excel report with "Per-Question" and "Summary" sheets |
| `evaluation_summary.txt` | Human-readable summary with diagnostics |

## Current Evaluation Results (as of latest run)

**50 Questions Evaluated**

| Metric | Average | Status |
|---|---:|---|
| Context Precision | 0.938 | 🟢 GREEN |
| Context Recall | 0.953 | 🟢 GREEN |
| Context Relevancy | 0.916 | 🟢 GREEN |
| **Faithfulness** | **0.974** | 🟢 GREEN |
| Answer Relevancy | 0.961 | 🟢 GREEN |
| **Exact Match** | **1.000** | 🟢 GREEN |

**Thresholds**: Green ≥ 0.80 | Yellow ≥ 0.50 | Red < 0.50

**Strengths**: Excellent faithfulness and numeric accuracy — critical for a compliance tool.  
**Area to watch**: Some questions show minor context precision/recall gaps.

## How to Run the Evaluation

### Prerequisites

- Python 3.10+
- `GROQ_API_KEY` in `.env` (same as main app)
- The regulation PDF at `sample_testing/DPDPA_2023_official.pdf`

### Step 1: Generate RAG Responses

```bash
cd evaluation
python step1_generate_responses.py
```

### Step 2: Run Evaluation & Generate Reports

```bash
python step2_run_evaluation.py
```

Outputs will be saved in the `results/` folder.

## Customization

### Adding New Questions

1. Add rows to `evaluation_test_dataset.csv`
2. Re-run `step1_generate_responses.py` (it is resumable)
3. Re-run `step2_run_evaluation.py`

### Changing Retrieval Parameters

Edit the following in `rag_pipeline.py`:

- `k` value in `get_retriever()`
- `chunk_size` / `chunk_overlap` in `get_vectorstore()`

### Modifying Judge Prompts

Edit the prompts inside `step2_run_evaluation.py`:

- `judge_context_quality`
- `judge_answer_quality`

## Diagnostic Guidance

- **High Precision + Low Recall** → Increase `k` or improve chunking
- **High Recall + Low Faithfulness** → Strengthen the system prompt in `rag_pipeline.py`
- **Low Exact Match** → Check `numeric_match.py` or improve prompt for exact copying

---

Part of the **COMPLY.AI Regulatory Intelligence System**  
Built to ensure reliable, hallucination-free answers on Indian data protection law.
