"""
numeric_match.py
----------------
Exact‑match metric for numeric values found in text.

The module extracts numbers from both digit strings (e.g., "Rs. 10,00,000")
and spelled‑out words in the Indian numbering system (e.g., "two hundred
and fifty crore"). It returns the fraction of ground‑truth numbers that
also appear in the generated answer.

If the ground truth contains no numbers, the metric returns None.
"""

import re

ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {
    "hundred": 100, "thousand": 1000, "lakh": 100000, "lac": 100000,
    "million": 1000000, "crore": 10000000, "billion": 1000000000,
}
CONNECTOR = {"and"}
VOCAB = set(ONES) | set(TENS) | set(SCALES)


def _words_to_number(tokens):
    """Convert a list of word tokens into an integer."""
    result = 0
    current = 0
    has_value = False
    for w in tokens:
        if w in CONNECTOR:
            continue
        if w in ONES:
            current += ONES[w]
            has_value = True
        elif w in TENS:
            current += TENS[w]
            has_value = True
        elif w == "hundred":
            current = (current if current else 1) * 100
            has_value = True
        elif w in SCALES:
            scale = SCALES[w]
            result += (current if current > 0 else 1) * scale
            current = 0
            has_value = True
    result += current
    return result if has_value else None


def extract_word_numbers(text):
    """Extract numeric values from spelled‑out numbers in the text."""
    words = re.findall(r"[A-Za-z]+", text.lower())
    runs, current = [], []
    for w in words:
        if w in VOCAB or w in CONNECTOR:
            current.append(w)
        else:
            if current:
                runs.append(current)
                current = []
    if current:
        runs.append(current)

    values = []
    for run in runs:
        while run and run[0] in CONNECTOR:
            run = run[1:]
        while run and run[-1] in CONNECTOR:
            run = run[:-1]
        if not run:
            continue
        if not any(w in ONES or w in TENS or w in SCALES for w in run):
            continue
        val = _words_to_number(run)
        if val is not None:
            values.append(val)
    return values


def extract_digit_numbers(text):
    """Extract numeric values from digit strings (with optional currency symbols)."""
    pattern = r"(?:₹|rs\.?|inr)?\s*\d[\d,]*(?:\.\d+)?"
    found = re.findall(pattern, text, flags=re.IGNORECASE)
    values = []
    for f in found:
        cleaned = re.sub(r"[^\d.]", "", f).strip(".")
        if not cleaned:
            continue
        try:
            values.append(float(cleaned) if "." in cleaned else int(cleaned))
        except ValueError:
            pass
    return values


def extract_all_numbers(text):
    """Return a set of all numeric values (both digit and word forms) found in the text."""
    if not text:
        return set()
    vals = set()
    for v in extract_digit_numbers(text):
        vals.add(float(v))
    for v in extract_word_numbers(text):
        vals.add(float(v))
    return vals


def exact_match_score(ground_truth: str, answer: str):
    """
    Compute the fraction of ground‑truth numbers that appear in the answer.

    Returns:
        float (0.0–1.0) or None if ground_truth contains no numbers.
    """
    gt_numbers = extract_all_numbers(ground_truth)
    if not gt_numbers:
        return None
    ans_numbers = extract_all_numbers(answer)
    matched = gt_numbers & ans_numbers
    return len(matched) / len(gt_numbers)