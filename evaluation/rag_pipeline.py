"""
rag_pipeline.py
---------------
RAG pipeline that retrieves relevant chunks from a PDF regulation document
and generates an answer using a Groq LLM.

The configuration (chunk size, overlap, embedding model, retriever k,
system prompt, and generation parameters) is identical to the main
application's RAG engine.
"""

import os
import re
import time
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, RateLimitError, APIStatusError, APIConnectionError

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
THIS_DIR = Path(__file__).resolve().parent
BASE_DIR = THIS_DIR.parent

load_dotenv(BASE_DIR / ".env")

GROQ_MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Embeddings + Vectorstore
# ---------------------------------------------------------------------------
_embeddings = None
_vectorstore_cache = {}


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def get_vectorstore(file_path: str):
    """Load or build a Chroma vector store for the given PDF file."""
    file_path = str(file_path)
    if file_path in _vectorstore_cache:
        return _vectorstore_cache[file_path]

    content_hash = hashlib.md5(open(file_path, "rb").read()).hexdigest()
    persist_dir = str(BASE_DIR / "data" / f"chroma_{content_hash}")
    embeddings = get_embeddings()

    if os.path.isdir(persist_dir) and os.listdir(persist_dir):
        print(f"   (re‑using existing vector index: {persist_dir})")
        vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    else:
        print(f"   (building new vector index at: {persist_dir})")
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=300,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks = text_splitter.split_documents(docs)

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_dir,
        )
    _vectorstore_cache[file_path] = vectorstore
    return vectorstore


def get_retriever(file_path: str):
    vs = get_vectorstore(file_path)
    return vs.as_retriever(search_kwargs={"k": 8})


# ---------------------------------------------------------------------------
# Query expansion
# ---------------------------------------------------------------------------
def expand_query(question: str) -> list:
    """Generate additional query variants to improve retrieval recall."""
    expansions = [question]
    if "penalty" in question.lower() or "fine" in question.lower():
        expansions.append(question.replace("penalty", "monetary penalty"))
        expansions.append(question.replace("penalty", "maximum amount"))
    if "section" in question.lower():
        match = re.search(r"section\s*(\d+)", question, re.IGNORECASE)
        if match:
            sec_num = match.group(1)
            expansions.append(f"breach of section {sec_num}")
            expansions.append(f"penalty for section {sec_num}")
    return expansions


def retrieve_contexts(file_path: str, question: str):
    """Return deduplicated chunk texts retrieved for the question."""
    retriever = get_retriever(file_path)
    queries = expand_query(question)
    all_docs = []
    seen = set()
    for q in queries:
        docs = retriever.invoke(q)
        for d in docs:
            if d.page_content not in seen:
                seen.add(d.page_content)
                all_docs.append(d)
    if not all_docs:
        all_docs = retriever.invoke(question)
    return [d.page_content for d in all_docs]


# ---------------------------------------------------------------------------
# Groq client + retry wrapper
# ---------------------------------------------------------------------------
_groq_client = None


def get_groq_client():
    global _groq_client
    if _groq_client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError(
                f"GROQ_API_KEY not found. Ensure a .env file with the key exists at {BASE_DIR / '.env'}"
            )
        _groq_client = Groq(api_key=key)
    return _groq_client


def groq_chat(messages, temperature=0.0, max_tokens=2048, json_mode=False, max_retries=6):
    """
    Call the Groq chat completion API with exponential backoff on errors.

    If json_mode=True, the response is requested in JSON format.
    """
    client = get_groq_client()
    delay = 5
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            kwargs = dict(
                model=GROQ_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            completion = client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content
        except RateLimitError as e:
            last_err = e
            wait = delay
            try:
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    wait = float(retry_after) + 1
            except Exception:
                pass
            print(f"      [rate limit] waiting {wait:.0f}s (attempt {attempt}/{max_retries})...")
            time.sleep(wait)
            delay = min(delay * 2, 60)
        except APIStatusError as e:
            last_err = e
            if json_mode and getattr(e, "status_code", None) == 400:
                print("      [json mode rejected by API] retrying without response_format...")
                json_mode = False
                continue
            print(f"      [API error {getattr(e, 'status_code', '?')}] retrying in {delay}s "
                  f"(attempt {attempt}/{max_retries})...")
            time.sleep(delay)
            delay = min(delay * 2, 60)
        except APIConnectionError as e:
            last_err = e
            print(f"      [connection error] retrying in {delay}s (attempt {attempt}/{max_retries})...")
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError(f"Groq API call failed after {max_retries} retries: {last_err}")


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
RAG_SYSTEM_PROMPT = (
    "You are a strict compliance analyst. Your task is to extract EXACT information from the provided regulation text.\n"
    "IMPORTANT RULES:\n"
    "1. If the user asks about a penalty for a specific section (e.g., Section 9), find the exact entry in the provided context that mentions that section number.\n"
    "2. DO NOT guess the serial number or amount. Copy the penalty amount and the description EXACTLY as written.\n"
    "3. If you find a list (like a Schedule), verify the section number mentioned in the description (e.g., 'under section 9') matches the user's question.\n"
    "4. If multiple entries exist, do not confuse them. Only choose the one where the description explicitly contains the requested section number.\n"
    "5. Output the exact text of the matching entry. For example: 'Sl. No. X: [description]. Penalty: [exact amount].'\n"
    "6. If you cannot find an exact match, state: 'This specific penalty is not found in the provided text.'\n"
    "7. Whenever you quote or summarize a definition or provision, explicitly state the FULL Section (and sub-section/clause) it comes from, e.g. write \"Section 2(i): ...\" or \"...as per Section 8(5)\" - never output a bare clause marker like \"(i)\" or \"(5)\" on its own without naming its parent Section. If the user's question already names a Section, use that number. Otherwise, identify the correct Section from the structure of the provided context (e.g., a lettered list under a 'Definitions' heading belongs to Section 2)."
)


def build_used_context(contexts):
    """Concatenate contexts, truncating to 12,000 characters."""
    context = "\n\n".join(contexts)
    if len(context) > 12000:
        context = context[:12000] + "\n...[CONTEXT TRUNCATED]"
    return context


def generate_answer(question: str, contexts: list):
    """Generate an answer using the RAG pipeline."""
    used_context = build_used_context(contexts)
    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": f"REGULATION CONTEXT:\n{used_context}\n\nQUESTION: {question}"},
    ]
    answer = groq_chat(messages, temperature=0.0, max_tokens=2048)
    return answer, used_context