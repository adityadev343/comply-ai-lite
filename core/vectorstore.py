import os
import hashlib
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- Lazy Load Embeddings (only once) ---
@st.cache_resource
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

@st.cache_resource
def get_vectorstore(file_path: str):
    """Builds a vector store from a PDF file."""
    # Load and chunk
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    
    # Improved splitter – no "." to avoid breaking structured lists
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,                # increased from 800
        chunk_overlap=300,              # increased from 100
        separators=["\n\n", "\n", " ", ""]   # removed "." – now splits on paragraphs, lines, spaces, and chars
    )
    chunks = text_splitter.split_documents(docs)
    
    # Generate a unique persist directory based on file content
    content_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
    persist_dir = f"./data/chroma_{content_hash}"
    
    # Embed and store
    embeddings = get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
    )
    return vectorstore

def get_retriever(file_path: str):
    """Returns a retriever function for the uploaded regulation."""
    vs = get_vectorstore(file_path)
    return vs.as_retriever(search_kwargs={"k": 20})   # increased from 12 to catch related chunks