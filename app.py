import os
import re
import numpy as np
import streamlit as st
import fitz
from supabase import create_client
from openai import OpenAI
from agents.router import run_orchestrator, list_agents

SUPABASE_URL = "https://lvthchgaspfbuybtrkoe.supabase.co"
SUPABASE_KEY = "sb_secret_Uft6Yv-x6Wf3j7_T5BjniQ_6Bzj-dUC"
BUCKET_NAME = "contratos"

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bucket = supabase.storage.from_(BUCKET_NAME)

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

# --- Tema rosa elegante ---
style = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

:root{
    --rosa-claro: #d69d96;
    --rosa-oscuro: #966368;
    --cafe-main: #4f3b06;
    --cafe-soft: #6a5320;
    --beige: #d1c18a;
    --blanco: #ffffff;
}

/* Fondo degradado (como te gustaba) */
[data-testid="stAppViewContainer"]{
    background: linear-gradient(180deg, #d69d96 0%, #966368 100%);
}

/* Fuente global */
html, body, [class*="css"]{
    font-family: "Inter", sans-serif !important;
    color: var(--cafe-main);
}

/* Contenedor principal */
.main .block-container{
    background-color: rgba(255, 255, 255, 0.92);
    padding: 2rem 2.5rem;
    border-radius: 20px;
    box-shadow: 0 12px 35px rgba(0,0,0,0.15);
    margin-top: 1.5rem;
}

/* Título */
h1{
    color: var(--cafe-main) !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
}

/* Sidebar */
[data-testid="stSidebar"]{
    background-color: var(--rosa-oscuro) !important;
}

[data-testid="stSidebar"] *{
    color: var(--beige) !important;
}

/* Tabs */
[data-testid="stTabs"] button{
    background-color: rgba(79, 59, 6, 0.08) !important;
    color: var(--cafe-soft) !important;
    border-radius: 14px !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 0.4rem 1rem;
}

[data-testid="stTabs"] button[aria-selected="true"]{
    background-color: var(--cafe-main) !important;
    color: white !important;
}

/* Botones */
.stButton > button{
    background-color: var(--cafe-main) !important;
    color: white !important;
    border-radius: 14px;
    padding: 0.55rem 1.4rem;
    font-weight: 600;
    border: none;
    transition: all 0.2s ease;
}

.stButton > button:hover{
    background-color: var(--rosa-oscuro) !important;
    transform: translateY(-1px);
}

/* Inputs */
input, textarea, .stTextInput input, .stTextArea textarea{
    background-color: #fff !important;
    border-radius: 12px !important;
    border: 1.8px solid rgba(150, 99, 104, 0.35) !important;
    color: var(--cafe-main) !important;
}

/* Selectbox */
div[data-baseweb="select"] > div{
    background-color: white !important;
    border-radius: 12px !important;
    border: 1.8px solid rgba(150, 99, 104, 0.35) !important;
}

/* Alerts */
[data-testid="stAlert"]{
    background-color: var(--beige) !important;
    color: var(--cafe-main) !important;
    border-radius: 14px;
    border: none;
}

/* Expander */
[data-testid="stExpander"]{
    background-color: rgba(255,255,255,0.35);
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.25);
}


/* Textos generales (labels, markdown, etc.) */

[data-testid="stMarkdownContainer"] p {
    font-size: 17px !important;
    font-weight: 600 !important;
}

/* Labels de inputs */
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stSelectbox"] label {
    font-size: 17px !important;
    font-weight: 600 !important;
    color: #2b1d0e !important;
}

/* Checkbox labels */
[data-testid="stCheckbox"] label {
    font-size: 17px !important;
    font-weight: 600 !important;
    color: #2b1d0e !important;
}

/* Caja INFO (st.info) */

/* Texto dentro del info */
[data-testid="stAlert"] p {
    color: #2b1d0e !important;
    font-weight: 600 !important;
    font-size: 16px !important;
}

/* Bullet pointss dentro del info */
[data-testid="stAlert"] li {
    color: #2b1d0e !important;
    font-weight: 500 !important;
    font-size: 15.5px !important;
}

</style>
"""

st.markdown(style, unsafe_allow_html=True)

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
        embs.append(embed_texts(texts[i:i + 64]))
    return docs, np.vstack(embs)


def retrieve_context(question: str, docs, doc_embs, k: int):
    q_emb = embed_texts([question])
    sims = cosine_sim_matrix(doc_embs, q_emb).reshape(-1)
    top_idx = np.argsort(-sims)[:k]
    selected = [docs[int(i)] for i in top_idx]
    context = "\n\n".join(
        [f"Source: {d['file']} (page {d['page']}, chunk {d['chunk']})\n{d['text']}"
         for d in selected]
    )
    return context, selected


def ask_llm(question: str, context: str):
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a legal assistant. Answer ONLY using the provided context. If missing, say you don't know."
            },
            {
                "role": "user",
                "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
            }
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


def safe_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return name or "upload.bin"


def upload_to_bucket(file_bytes: bytes, dest_path: str, content_type: str | None = None):
    opts = {"content-type": content_type} if content_type else {}
    return bucket.upload(dest_path, file_bytes, file_options=opts)


st.title("Contratos")

tab_consulta, tab_upload = st.tabs(["Consulta", "Subir documentos"])

with tab_upload:
    st.subheader("Subir documentos a la base de datos")
    st.caption(f"Bucket: {BUCKET_NAME}")

    target_folder = st.text_input("Carpeta destino (opcional)", value="")
    uploaded_files = st.file_uploader(
        "Selecciona uno o varios archivos (PDF recomendado)",
        type=None,
        accept_multiple_files=True,
    )

    colu1, colu2 = st.columns(2)
    with colu1:
        overwrite = st.checkbox("Sobrescribir si ya existe", value=False)
    with colu2:
        clear_cache = st.checkbox("Limpiar caché del índice al subir", value=True)

    if st.button("Subir al bucket", disabled=not uploaded_files):
        ok = 0
        fail = 0

        for uf in uploaded_files:
            try:
                fname = safe_filename(uf.name)
                dest = f"{target_folder.strip().strip('/')}/{fname}".strip("/") if target_folder else fname

                if not overwrite:
                    existing = bucket.list(path=target_folder.strip().strip("/") if target_folder else "")
                    existing_names = {x["name"] for x in existing}
                    if fname in existing_names:
                        st.warning(f"Ya existe y no se sobrescribió: {dest}")
                        fail += 1
                        continue

                file_bytes = uf.getvalue()
                content_type = uf.type or "application/octet-stream"
                upload_to_bucket(file_bytes, dest, content_type=content_type)
                st.success(f"Subido: {dest} ({len(file_bytes):,} bytes)")
                ok += 1
            except Exception as e:
                st.error(f"Error subiendo {uf.name}: {e}")
                fail += 1

        st.info(f"Resultado: {ok} subidos, {fail} con error")

        if clear_cache:
            st.cache_resource.clear()
            st.success("Caché limpiada. En la siguiente consulta se reindexará.")

    st.divider()
    st.subheader("Archivos en el bucket")
    try:
        root_files = bucket.list(path="")
        if root_files:
            for it in root_files:
                st.write(f"- {it.get('name')}")
        else:
            st.write("No hay archivos en la raíz del bucket.")
    except Exception as e:
        st.error(f"No pude listar archivos: {e}")

with tab_consulta:
    with st.sidebar:
        max_pages = st.slider("Max pages per PDF", 1, 200, 60)
        chunk_chars = st.slider("Chunk size", 400, 2000, 1200, step=100)
        overlap = st.slider("Overlap", 0, 400, 200, step=50)
        top_k = st.slider("Top-K", 1, 12, 6)
        if st.button("Rebuild index"):
            st.cache_resource.clear()

    agents = list_agents()

    mode = st.radio(
        "Modo de consulta",
        options=["General", "Por agente"],
        index=0,
        horizontal=True,
    )

    selected_agent_key = None

    if mode == "Por agente":
        selected_agent_key = st.selectbox(
            "Selecciona un agente",
            options=list(agents.keys()),
            format_func=lambda k: agents[k]["label"],
        )
        if selected_agent_key:
            st.info(agents[selected_agent_key]["description"])

    question = st.text_area("Pregunta", height=120)
    ask = st.button("Preguntar")

    if ask and question.strip():
        with st.spinner("Procesando..."):
            docs, doc_embs = build_index(max_pages, chunk_chars, overlap)
            if not docs:
                st.error("No PDFs found")
                st.stop()
            context, sources = retrieve_context(question, docs, doc_embs, top_k)

            if mode == "General":
                answer = ask_llm(question, context)
                results = {"general": answer}
            else:
                results = run_orchestrator(question, context, agent_key=selected_agent_key)

        st.subheader("Respuesta")

        for agent_name, answer in results.items():
            if agent_name == "general":
                st.markdown("### Asistente general")
            else:
                st.markdown(f"### {agents[agent_name]['label']}")
            st.write(answer)

        with st.expander("Fuentes"):
            for s in sources:
                st.markdown(f"*{s['file']}* — page {s['page']} — chunk {s['chunk']}")
                st.write(s["text"])
                st.divider()