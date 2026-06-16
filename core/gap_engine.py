import os
import json
import streamlit as st
from groq import Groq
from core.pdf_reader import extract_text_from_pdf
from core.vectorstore import get_retriever

@st.cache_resource
def get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

def expand_queries(base_query: str) -> list:
    """Generate multiple retrieval queries to cover different aspects of the regulation."""
    return [
        base_query,
        base_query + " obligations duties requirements",
        base_query + " prohibitions restrictions shall not",
        base_query + " consent notice breach erasure retention",
        base_query + " children parental consent tracking behavioural monitoring",
        base_query + " data protection officer impact assessment audit",
        base_query + " grievance redressal nomination",
        base_query + " transfer international",
        base_query + " definitions interpretation"
    ]

def filter_conditional_gaps(gaps, classification):
    """
    If classification is "No", remove any gap whose obligation description
    starts with "CONDITIONAL: " – these are obligations that the LLM
    identified as applying only to special categories.
    """
    if classification != "No":
        return gaps
    
    filtered = []
    for gap in gaps:
        obligation = gap.get("obligation", "")
        # Remove if the obligation is explicitly marked as conditional
        if obligation.startswith("CONDITIONAL: "):
            continue
        filtered.append(gap)
    return filtered

def run_gap_analysis(regulation_text: str, policy_file, company_classification: str = "Not specified") -> dict:
    """
    Compares policy against regulation using a generic, regulation‑agnostic approach.
    company_classification: "Yes", "No", or "Not specified"
    """
    client = get_groq_client()
    
    # Extract policy text
    if policy_file.name.endswith('.pdf'):
        policy_text = extract_text_from_pdf(policy_file)
    else:
        policy_file.seek(0)
        policy_text = policy_file.read().decode('utf-8', errors='ignore')
    
    if not st.session_state.get('regulation_file_path'):
        return {"compliance_score": 0, "gaps": [{
            "obligation": "Error",
            "severity": "high",
            "what_is_missing": "Regulation file not found.",
            "rationale": "Please re‑upload the regulation.",
            "recommended_action": "Re‑upload regulation."
        }], "met": []}
    
    retriever = get_retriever(st.session_state.regulation_file_path)
    
    # --- 1. Multi‑query retrieval to cover all types of obligations ---
    base = "obligations duties requirements prohibitions consent breach erasure children"
    queries = expand_queries(base)
    all_docs = []
    seen = set()
    for q in queries:
        docs = retriever.invoke(q)
        for d in docs:
            if d.page_content not in seen:
                seen.add(d.page_content)
                all_docs.append(d)
    
    if not all_docs:
        return {"compliance_score": 0, "gaps": [{
            "obligation": "Error",
            "severity": "high",
            "what_is_missing": "No regulation content retrieved.",
            "rationale": "The regulation may not be properly indexed.",
            "recommended_action": "Re‑index the regulation."
        }], "met": []}
    
    # Combine retrieved chunks (deduplicated)
    reg_context = "\n\n".join([d.page_content for d in all_docs])
    if len(reg_context) > 12000:
        reg_context = reg_context[:12000] + "\n...[CONTEXT TRUNCATED]"
    
    if len(policy_text) > 15000:
        policy_to_send = policy_text[:15000] + "\n...[POLICY TRUNCATED]"
    else:
        policy_to_send = policy_text
    
    # --- 2. Build the classification instruction (dynamic marking) ---
    if company_classification == "No":
        class_instruction = (
            "The company does NOT fall under any special category. "
            "Therefore, you MUST mark any obligation that is conditional on such a category "
            "by prefixing its 'obligation' field with 'CONDITIONAL: '. "
            "Do NOT list it as a gap – but still include it in the 'met' list as 'Conditional – not applicable'."
        )
    elif company_classification == "Not specified":
        class_instruction = (
            "The company has NOT specified whether it falls under any special category. "
            "If you find obligations that are conditional on such a category, mark them with 'CONDITIONAL: ' "
            "and flag them as a gap with MEDIUM severity, recommending that the company clarifies its status."
        )
    else:  # "Yes"
        class_instruction = (
            "The company IS a member of a special category. "
            "Include all obligations – do NOT mark any as conditional."
        )
    
    # --- 3. Enhanced prompt with dynamic marking instruction ---
    prompt = f"""
You are an expert compliance auditor. Compare the provided COMPANY POLICY against the REGULATION.

**COMPANY CLASSIFICATION STATUS:** {company_classification}
{class_instruction}

**TASK:**
1. **Extract ALL obligations** from the regulation – these include:
   - Mandatory requirements (e.g., “shall”, “must”).
   - Prohibitions (e.g., “shall not”).
   - Definitions that affect compliance (e.g., age of a child).
   - Conditional obligations – these are obligations that only apply if the company falls into a special category (like "Significant Data Fiduciary"). 
     *Look for phrases like "Significant Data Fiduciary", "if you are a ...", "for such class of Data Fiduciaries" in the regulation text.*

2. **For each obligation**, check the company policy:
   - If the policy fully addresses it → mark as **met**.
   - If partially addressed → mark as a **gap** with appropriate severity.
   - If not addressed at all → mark as a **gap**.
   - **CRITICAL**: For conditional obligations, apply the classification status:
       * If classification is **"No"**, prefix the obligation with 'CONDITIONAL: ' and do NOT list it as a gap – put it in 'met' as 'Conditional – not applicable'.
       * If classification is **"Not specified"**, prefix with 'CONDITIONAL: ' and flag as a gap with MEDIUM severity.
       * If classification is **"Yes"**, treat it as a normal obligation (no prefix).

3. **Severity guidelines (generic):**
   - **HIGH**: Children (consent, tracking, targeted advertising, detrimental effect), breach notification, erasure upon consent withdrawal, fundamental rights.
   - **MEDIUM**: Security safeguards, impact assessments, grievance redressal, audits, DPO (if applicable), data quality.
   - **LOW**: Administrative (contact details, nomination, publishing info).

4. **Compliance score**: Calculate percentage of met obligations out of total (excluding conditional ones that are clearly not applicable per classification).

5. **Return ONLY valid JSON** with this structure:
   {{
     "compliance_score": <integer 0-100>,
     "gaps": [
       {{
         "obligation": "<Name or description – prefix with 'CONDITIONAL: ' if applicable>",
         "severity": "<'high'/'medium'/'low'>",
         "what_is_missing": "<What's missing>",
         "rationale": "<Why risk>",
         "recommended_action": "<Fix>"
       }}
     ],
     "met": ["<Obligation 1>", "<Obligation 2>", ...]
   }}

REGULATION (context):
{reg_context}

COMPANY POLICY:
{policy_to_send}

JSON:
"""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4096,
        )
        raw = completion.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        result = json.loads(raw)
        
        # --- 4. Post‑processing: filter out conditional gaps if classification is "No" ---
        original_gaps = result.get("gaps", [])
        result["gaps"] = filter_conditional_gaps(original_gaps, company_classification)
        
        # --- 5. Recalculate score based on filtered gaps ---
        total_obligations = len(result.get("met", [])) + len(result["gaps"])
        if total_obligations > 0:
            result["compliance_score"] = int((len(result.get("met", [])) / total_obligations) * 100)
        else:
            result["compliance_score"] = 100
            
        return result
    except Exception as e:
        return {
            "compliance_score": 0,
            "gaps": [{
                "obligation": "Parsing Error",
                "severity": "high",
                "what_is_missing": str(e),
                "rationale": "The AI response could not be parsed as JSON.",
                "recommended_action": "Try again."
            }],
            "met": []
        }