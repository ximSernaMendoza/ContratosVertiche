import os
import re
import numpy as np
import streamlit as st
import fitz
from supabase import create_client
from openai import OpenAI


SUPABASE_URL = "https://lvthchgaspfbuybtrkoe.supabase.co"
SUPABASE_KEY = "sb_secret_Uft6Yv-x6Wf3j7_T5BjniQ_6Bzj-dUC"

BUCKET_NAME = "contratos"

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bucket = supabase.storage.from_(BUCKET_NAME)

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

def pdf_bytes_to_pages(pdf_bytes: bytes, max_pages: int):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i in range(min(len(doc), max_pages)):
        t = doc[i].get_text("text").strip()
        if t:
            pages.append((i + 1, t))
    return pages

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def chunk_text(text: str, chunk_chars: int, overlap: int):
    text = clean_text(text)
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_chars)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks

def embed_texts(texts):
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return np.array([d.embedding for d in resp.data], dtype=np.float32)

def cosine_sim_matrix(a: np.ndarray, b: np.ndarray):
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a_norm @ b_norm.T

@st.cache_resource(show_spinner=True)
def build_index(max_pages: int, chunk_chars: int, overlap: int):
    files = bucket.list(path="")
    pdf_files = [f["name"] for f in files if f["name"].lower().endswith(".pdf")]
    docs = []
    texts = []
    for name in pdf_files:
        pdf_bytes = bucket.download(name)
        pages = pdf_bytes_to_pages(pdf_bytes, max_pages)
        for page_num, page_text in pages:
            for ci, chunk in enumerate(chunk_text(page_text, chunk_chars, overlap)):
                docs.append({"file": name, "page": page_num, "chunk": ci, "text": chunk})
                texts.append(chunk)
    if not texts:
        return [], np.zeros((0, 1), dtype=np.float32)
    embs = []
    for i in range(0, len(texts), 64):
        embs.append(embed_texts(texts[i:i+64]))
    return docs, np.vstack(embs)

def retrieve_context(question: str, docs, doc_embs, k: int):
    q_emb = embed_texts([question])
    sims = cosine_sim_matrix(doc_embs, q_emb).reshape(-1)
    top_idx = np.argsort(-sims)[:k]
    selected = [docs[int(i)] for i in top_idx]
    context = "\n\n".join(
        [f"Source: {d['file']} (page {d['page']}, chunk {d['chunk']})\n{d['text']}" for d in selected]
    )
    return context, selected

def ask_llm(question: str, context: str):
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a legal assistant. Answer ONLY using the provided context. If missing, say you don't know."},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"}
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""

st.title("Contratos")

with st.sidebar:
    max_pages = st.slider("Max pages per PDF", 1, 200, 60)
    chunk_chars = st.slider("Chunk size", 400, 2000, 1200, step=100)
    overlap = st.slider("Overlap", 0, 400, 200, step=50)
    top_k = st.slider("Top-K", 1, 12, 6)
    if st.button("Rebuild index"):
        st.cache_resource.clear()

question = st.text_area("Pregunta", height=120)
ask = st.button("Preguntar")

if ask and question.strip():
    with st.spinner("Procesando..."):
        docs, doc_embs = build_index(max_pages, chunk_chars, overlap)
        if not docs:
            st.error("No PDFs found")
            st.stop()
        context, sources = retrieve_context(question, docs, doc_embs, top_k)
        answer = ask_llm(question, context)

    st.subheader("Respuesta")
    st.write(answer)

    with st.expander("Fuentes"):
        for s in sources:
            st.markdown(f"*{s['file']}* — page {s['page']} — chunk {s['chunk']}")
            st.write(s["text"])
            st.divider()