import os
import json
import streamlit as st
from groq import Groq
from core.vectorstore import get_retriever

@st.cache_resource
def get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_policy_guidance(regulation_text: str, company_data: dict) -> dict:
    """
    Generates policy guidance using relevant regulation chunks.
    company_data may contain 'classification' key: "Yes", "No", "Not specified"
    """
    client = get_groq_client()
    
    if not st.session_state.get('regulation_file_path'):
        return {
            "readiness_score": 0,
            "summary": "Regulation file not found. Please re-upload.",
            "sections": [],
            "priority_actions": ["Re-upload the regulation file."],
            "risk_areas": ["No regulation loaded."]
        }
    
    retriever = get_retriever(st.session_state.regulation_file_path)
    docs = retriever.invoke("obligations requirements compliance reporting disclosures penalties consent")
    
    if not docs:
        return {
            "readiness_score": 0,
            "summary": "No regulation content retrieved. Please re-index.",
            "sections": [],
            "priority_actions": ["Re-index the regulation."],
            "risk_areas": ["Regulation content missing."]
        }
    
    reg_context = "\n\n".join([d.page_content for d in docs])
    if len(reg_context) > 10000:
        reg_context = reg_context[:10000] + "\n...[TRUNCATED]"
    
    classification = company_data.get("classification", "Not specified")
    
    # --- Build classification instruction ---
    if classification == "No":
        class_instruction = (
            "The company does NOT fall under any special category (e.g., 'Significant Data Fiduciary') that would trigger additional obligations. "
            "Therefore, when suggesting policy sections, DO NOT include mandatory requirements that are ONLY applicable to such categories. "
            "You may mention measures like DPO, DPIA, or independent audits ONLY as optional best practices, clearly marked as optional."
        )
    elif classification == "Not specified":
        class_instruction = (
            "The company has NOT specified whether it falls under any special category. "
            "If you find obligations that are conditional on such categories, include them as recommended actions, but also suggest that the company clarifies its status."
        )
    else:  # "Yes"
        class_instruction = (
            "The company IS a member of a special category (e.g., 'Significant Data Fiduciary'). "
            "Include ALL applicable obligations for such categories as MANDATORY sections. Specifically, include sections on:\n"
            "- Appointment of a Data Protection Officer (DPO) – based in India.\n"
            "- Independent data auditor.\n"
            "- Periodic Data Protection Impact Assessment (DPIA).\n"
            "- Periodic audit.\n"
            "These are NOT optional – they are required by law for this category."
        )
    
    # --- Enhanced prompt with strict rules ---
    prompt = f"""
You are a senior compliance advisor. A company has answered questions about their business.

COMPANY PROFILE:
- Name: {company_data.get('name', 'N/A')}
- What they do: {company_data.get('description', 'N/A')}
- Information flows: {company_data.get('information_flows', 'N/A')}
- Key stakeholders: {company_data.get('stakeholders', 'N/A')}
- Compliance concerns: {company_data.get('concerns', 'N/A')}
- Existing policies: {company_data.get('existing_policies', 'N/A')}
- Classification status: {classification}

{class_instruction}

REGULATION (context):
{reg_context}

TASK:
Generate a practical compliance guidance report tailored to THIS specific company.

CRITICAL RULES (MUST FOLLOW):
1. **Section References**: Always quote the EXACT section/article number AND the heading/title as it appears in the regulation text. If the exact number is not visible in the context, do NOT invent it – say "as per the applicable provisions of the Act" instead.

2. **Un-prescribed Timeframes**: If the regulation says "as may be prescribed" or "in such manner as may be prescribed", do NOT invent a specific number (e.g., 72 hours, 30 days). Instead, say "within the timeframe prescribed by the regulatory authority" or "as notified by the Board".

3. **Consent Manager**: A Consent Manager is a separate entity registered with the Board. A Data Fiduciary does NOT register as a Consent Manager – it may choose to use one or handle consent directly. Do NOT recommend that the company registers as a Consent Manager.

4. **Significant Data Fiduciary (SDF) – if classification is "Yes"**:
   - MUST include the following sections (these are mandatory):
     * Data Protection Officer (DPO) – based in India.
     * Independent data auditor.
     * Data Protection Impact Assessment (DPIA) – periodic.
     * Periodic audit.
   - Section reference for all these is Section 10 (Significant Data Fiduciary) – NOT Section 12 or others.

5. **Children's Data**: If the company processes any personal data that could include children (even indirectly), include a section on children's data protection (verifiable parental consent, prohibition of tracking/behavioural monitoring, and targeted advertising) – reference Section 9.

6. **Readiness Score**: Calculate the score as the percentage of applicable obligations that are met (or reasonably addressed) out of the total applicable obligations. If classification is "Yes", the total number of applicable obligations is higher – the score should reflect that (i.e., it will likely be lower than if classification is "No"). Do not just count sections – think about whether the company's profile and stated practices actually address each obligation.

7. **Return ONLY valid JSON** with the structure below. No markdown, no explanation, no additional text.

JSON STRUCTURE:
{{
  "readiness_score": <integer 0-100>,
  "summary": "<2‑sentence summary of their situation>",
  "sections": [
    {{
      "section_name": "<Policy section title>",
      "what_to_include": "<Plain English guidance for THIS company>",
      "sample_clause": "<Ready-to-adapt clause written for them>",
      "why_it_matters": "<Business risk if omitted>",
      "regulation_reference": "<Exact section number and title>"
    }}
  ],
  "priority_actions": ["<Action 1>", "<Action 2>"],
  "risk_areas": ["<Risk 1>", "<Risk 2>"]
}}

Generate 5‑7 sections. Make them specific to the company's business, not generic.
JSON:
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4096,
        )
        raw = completion.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        return json.loads(raw)
    except Exception as e:
        return {
            "readiness_score": 0,
            "summary": f"Error generating guidance: {str(e)}",
            "sections": [],
            "priority_actions": ["Check your API key and try again."],
            "risk_areas": ["Unable to parse AI response."]
        }