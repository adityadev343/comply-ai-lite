import os
import streamlit as st
from groq import Groq
from core.vectorstore import get_retriever

@st.cache_resource
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("❌ GROQ_API_KEY not found. Please add it in Streamlit Cloud Secrets or .env file.")
        raise ValueError("GROQ_API_KEY is required")
    return Groq(api_key=api_key)

def expand_query(question: str) -> list:
    """Generates alternative phrasings to improve retrieval recall."""
    # Simple expansion – can be extended with an LLM call if needed
    expansions = [question]
    if "penalty" in question.lower() or "fine" in question.lower():
        expansions.append(question.replace("penalty", "monetary penalty"))
        expansions.append(question.replace("penalty", "maximum amount"))
    if "section" in question:
        # Add a more generic version without the section number to catch the schedule
        import re
        match = re.search(r'section\s*(\d+)', question, re.IGNORECASE)
        if match:
            sec_num = match.group(1)
            expansions.append(f"breach of section {sec_num}")   # simple form
            expansions.append(f"penalty for section {sec_num}")
    return expansions

def ask_question(regulation_text: str, question: str) -> str:
    """
    Uses RAG to answer questions about the regulation.
    regulation_text is kept for compatibility.
    """
    if not st.session_state.get('regulation_file_path'):
        return "⚠️ Regulation file path not found. Please re-upload."
    
    client = get_groq_client()
    retriever = get_retriever(st.session_state.regulation_file_path)
    
    # Expand query for better retrieval
    queries = expand_query(question)
    all_docs = []
    seen_contents = set()
    for q in queries:
        docs = retriever.invoke(q)
        for d in docs:
            if d.page_content not in seen_contents:
                seen_contents.add(d.page_content)
                all_docs.append(d)
    
    # If no docs from expanded queries, fallback to original
    if not all_docs:
        all_docs = retriever.invoke(question)
    
    # Combine retrieved chunks (deduplicated)
    context = "\n\n".join([d.page_content for d in all_docs])
    
    # Truncate context safely
    if len(context) > 12000:
        context = context[:12000] + "\n...[CONTEXT TRUNCATED]"
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict compliance analyst. Your task is to extract EXACT information from the provided regulation text.\n"
                        "IMPORTANT RULES:\n"
                        "1. If the user asks about a penalty for a specific section (e.g., Section 9), find the exact entry in the provided context that mentions that section number.\n"
                        "2. DO NOT guess the serial number or amount. Copy the penalty amount and the description EXACTLY as written.\n"
                        "3. If you find a list (like a Schedule), verify the section number mentioned in the description (e.g., 'under section 9') matches the user's question.\n"
                        "4. If multiple entries exist, do not confuse them. Only choose the one where the description explicitly contains the requested section number.\n"
                        "5. Output the exact text of the matching entry. For example: 'Sl. No. X: [description]. Penalty: [exact amount].'\n"
                        "6. If you cannot find an exact match, state: 'This specific penalty is not found in the provided text.'"
                    )
                },
                {
                    "role": "user",
                    "content": f"REGULATION CONTEXT:\n{context}\n\nQUESTION: {question}"
                }
            ],
            temperature=0.0,
            max_tokens=2048
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error calling Groq API: {str(e)}"
