"""
step1_generate_responses.py
----------------------------
Run the RAG pipeline over all questions in the test dataset and save the raw
outputs (retrieved contexts, truncated context used, and generated answer)
to a JSON file for later evaluation.

The script is resumable: it skips questions already present in the output file.
"""

import sys
import csv
import json
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from rag_pipeline import retrieve_contexts, generate_answer, get_retriever, BASE_DIR  # noqa: E402

CSV_PATH = THIS_DIR / "evaluation_test_dataset.csv"
PDF_PATH = BASE_DIR / "sample_testing" / "DPDPA_2023_official.pdf"
RESULTS_DIR = THIS_DIR / "results"
OUT_PATH = RESULTS_DIR / "rag_raw_outputs.json"

SLEEP_BETWEEN_QUESTIONS = 1.5


def load_existing():
    if OUT_PATH.exists():
        with open(OUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save(results):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def main():
    if not CSV_PATH.exists():
        print(f"ERROR: Test dataset not found at {CSV_PATH}")
        sys.exit(1)
    if not PDF_PATH.exists():
        print(f"ERROR: Regulation PDF not found at {PDF_PATH}")
        sys.exit(1)

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} questions from {CSV_PATH.name}")

    results = load_existing()
    done_questions = {r["question"] for r in results}
    if done_questions:
        print(f"Resuming: {len(done_questions)} questions already processed.\n")

    print("Building / loading the vector index from the regulation PDF...")
    get_retriever(str(PDF_PATH))
    print("Index ready.\n")

    total = len(rows)
    for i, row in enumerate(rows, 1):
        question = row["question"].strip()
        ground_truth = row["answer_ground_truth"].strip()

        if question in done_questions:
            print(f"[{i}/{total}] Skipping (already done): {question[:70]}")
            continue

        print(f"[{i}/{total}] Processing: {question[:80]}")
        try:
            contexts = retrieve_contexts(str(PDF_PATH), question)
            answer, used_context = generate_answer(question, contexts)
        except Exception as e:
            print(f"   !! FAILED: {e}")
            contexts, used_context, answer = [], "", f"[GENERATION FAILED: {e}]"

        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "contexts": contexts,
            "used_context": used_context,
            "answer": answer,
        })
        save(results)
        time.sleep(SLEEP_BETWEEN_QUESTIONS)

    print(f"\nDone. Saved {len(results)} results to {OUT_PATH}")
    print("Next: run step2_run_evaluation.py")


if __name__ == "__main__":
    main()