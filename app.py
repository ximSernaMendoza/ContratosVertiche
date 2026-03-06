import os
import re
import numpy as np
import streamlit as st
import fitz
from supabase import create_client
from openai import OpenAI
from agents.router import run_orchestrator, list_agents
from agents.finance_agent import extract_finance_numbers
from core.finance import FinanceInputs, project_cashflows
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import requests
from dateutil.relativedelta import relativedelta
from streamlit_calendar import calendar
from typing import Optional
import plotly.graph_objects as go

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="Asistente Virtual 1.0 | Vertiche",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------
# PALETA DE COLORES 
# ---------------------------
PINK_LIGHT = "#d69d96"
PINK_DARK  = "#966368"
BROWN_MAIN = "#4f3b06"
BROWN_SOFT = "#6a5320"
BEIGE      = "#d1c18a"

# ---------------------------
# CSS (SOLO FRONTEND)
# ---------------------------
st.markdown(
    f"""
    <style>
      /* ---- Base ---- */
      :root {{
        --pink-light: {PINK_LIGHT};
        --pink-dark:  {PINK_DARK};
        --brown-main: {BROWN_MAIN};
        --brown-soft: {BROWN_SOFT};
        --beige:      {BEIGE};
        --radius: 16px;
      }}

      /* Fondo general */
      .stApp {{
        background: {PINK_LIGHT}; #linear-gradient(180deg, #d69d96 0%, #966368 100%)
      }}

      /* BARRA SUPERIOR */
        header {{
        background: #d69d96 !important; #linear-gradient(180deg, #d69d96 0%, #966368 100%) 

      }}      

      /* Sidebar */
      section[data-testid="stSidebar"] {{
        background: {PINK_DARK};
        border-right: 1px solid rgba(209,193,138,0.25);
      }}
      section[data-testid="stSidebar"] * {{
        color: rgba(255,255,255,1);
      }}

      /* Títulos */
      h1, h2, h3 {{
        color: var(--brown-main);
        letter-spacing: -0.2px;
      }}
      .muted {{
        color: rgba(79,59,6,0.75);
      }}

      /* ---- Top Header ---- */
      .topbar {{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap: 1rem;
        padding: 1rem 1.2rem;
        border-radius: var(--radius);
        background: rgba(255,255,255,0.55);
        border: 1px solid rgba(79,59,6,0.14);
        backdrop-filter: blur(8px);
        box-shadow: 0 10px 30px rgba(79,59,6,0.10);
      }}
      .brand {{
        display:flex;
        align-items:center;
        gap:.75rem;
      }}
      .logo {{
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: linear-gradient(135deg, var(--pink-dark), var(--pink-light));
        box-shadow: 0 10px 20px rgba(150,99,104,0.30);
        border: 1px solid rgba(79,59,6,0.14);
      }}
      .brand-title {{
        font-weight: 700;
        color: var(--brown-main);
        font-size: 1.05rem;
        line-height: 1.1;
      }}
      .brand-sub {{
        font-size: 0.86rem;
        color: rgba(79,59,6,0.70);
      }}

      .status-pill {{
        display:flex;
        align-items:center;
        gap:.55rem;
        padding:0.4rem .75rem;
        border-radius: 999px;
        background: rgba(214,157,150,0.22);
        border: 1px solid rgba(150,99,104,0.25);
        color: var(--brown-main);
        font-size: 0.88rem;
        font-weight: 600;
      }}
      .dot {{
        width: 10px;
        height: 10px;
        border-radius: 999px;
        background: var(--pink-dark);
        box-shadow: 0 0 0 4px rgba(214,157,150,0.35);
      }}

      /* ---- Cards ---- */
      .card {{
        border-radius: var(--radius);
        background: rgba(255,255,255,0.60);
        border: 1px solid rgba(79,59,6,0.14);
        padding: 1rem;
        box-shadow: 0 12px 28px rgba(79,59,6,0.10);
        backdrop-filter: blur(10px);
      }}
      .kpi-row {{
        display:flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 0rem;
      }}
      .kpi {{
        flex: 1 1 150px;
        border-radius: 14px;
        padding: 0.4rem 1rem;
        background: rgba(255,255,255,0.60);
        border: 1px solid rgba(150,99,104,0.18);
      }}
      .kpi .label {{
        font-size: 1.1rem;
        color: var(--brown-main);
        font-weight: 600;
      }}
      .kpi .value {{
        font-size: 1.1rem;
        font-weight: 800;
        color: rgba(79,59,6,1);
        margin-top: .1rem;
      }}

      /* ---- Chat ---- */

      .msg {{
        display:flex;
        gap:.8rem;
        margin: .55rem 0;
        align-items:flex-end;
      }}
      .avatar {{
        width: 34px;
        height: 34px;
        border-radius: 12px;
        border: 1px solid rgba(79,59,6,0.14);
      }}
      .avatar.user {{
        background: {BROWN_SOFT};
      }}
      .avatar.bot {{
        background: linear-gradient(135deg, rgba(150,99,104,0.95), rgba(214,157,150,0.95));
      }}

      .bubble {{
        max-width: 78%;
        padding: .75rem .9rem;
        border-radius: 16px;
        border: 1px solid rgba(79,59,6,0.12);
        box-shadow: 0 10px 20px rgba(79,59,6,0.06);
      }}
      .bubble.user {{
        background: {PINK_DARK};
        color: rgba(255,255,255,1); 
        border-top-right-radius: 8px;
      }}
      .bubble.bot {{
        background: {PINK_LIGHT};
        color: var(--brown-main);
        border-top-left-radius: 8px;
      }}
      .meta {{
        font-size: .75rem;
        color: rgba(255,255,255,1);
        margin-top: .35rem;
      }}

      /* Chips */
      .chips {{
        display:flex;
        gap:.5rem;
        flex-wrap: wrap;
        margin: .75rem 0 1rem 0;
      }}
      /* Chips como botones */
    .chip-btn button {{
    padding: .45rem .7rem !important;
    border-radius: 999px !important;
    background: rgba(255,255,255,0.55) !important;
    border: 1px solid rgba(79,59,6,0.14) !important;
    color: var(--brown-main) !important;
    font-weight: 700 !important;
    font-size: .85rem !important;
    box-shadow: none !important;
    }}
    .chip-btn button:hover {{
    filter: brightness(0.98);
    transform: translateY(-1px);
    }}

      /* ---- Bottom input bar (fija) ---- */
      .bottom-bar {{
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 999;
        padding: .9rem 1rem;
        background: #d69d96; #linear-gradient(180deg, #d69d96 0%, #966368 100%)
        border-top: 1px solid rgba(79,59,6,0.14);
        backdrop-filter: blur(12px);
      }}
      .bottom-inner {{
        max-width: 1200px;
        margin: 0 auto;
        display:flex;
        gap:.6rem;
        align-items:center;
      }}
      .hint {{
        font-size: .85rem;
        color: rgba(79,59,6,0.70);
      }}

      /* ---- Buttons / inputs ---- */
      div.stButton > button {{
        border-radius: 12px !important;
        border: 1px solid rgba(79,59,6,0.18) !important;
        background: rgba(255,255,255,0.85) !important;
        color: var(--brown-main) !important;
        font-weight: 700 !important;
        padding: 0.01rem .7rem !important;
        box-shadow: 0 10px 18px rgba(150,99,104,0.25) !important;
      }}
      div.stButton > button:hover {{
        filter: brightness(0.98);
        transform: translateY(-1px);
      }}

     /* Inputs - texto escrito */
.stTextInput input,
.stTextArea textarea {{
    color: var(--brown-main) !important;
    border-radius: 1px !important;
    border: 1px solid rgba(255,255,255,0.85) !important;
    background: rgba(250,250,250,0.95) !important;
}}

/* Placeholder text */
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {{
    color: #966368 !important;   /* ← el color que quieres */
    opacity: 1 !important;
}}

      /* Tabs */
      .stTabs [data-baseweb="tab"] {{
        background: rgba(209,193,138,0.20);
        border: 1px solid rgba(79,59,6,0.14);
        border-radius: 12px;
        color: var(--brown-main);
        font-weight: 700;
        padding: .5rem .8rem;
      }}
      .stTabs [aria-selected="true"] {{
        background: rgba(214,157,150,0.22);
        border-color: rgba(150,99,104,0.30);
      }}

      /* Footer sutil */
      .footer {{
        margin-top: .9rem;
        font-size: .82rem;
        color: rgba(79,59,6,0.60);
      }}
      

      /* Quitar apariencia de botón */
section[data-testid="stSidebar"] .stButton button {{
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    color: #4f3b06 !important;
    font-weight: 500 !important;
    padding: 0 !important;
    text-align: left !important;
}}


/* Hover tipo link */
section[data-testid="stSidebar"] .stButton button:hover {{
    color: #966368 !important;
    text-decoration: underline !important;
}}

/* Espaciado limpio */
section[data-testid="stSidebar"] .stButton {{
    margin-bottom: 0.6rem;
}}

/* ----------------------------
   Drag & Drop - File Uploader
---------------------------- */

[data-testid="stFileUploader"] {{
  border: 2px dashed #966368 !important;
  border-radius: 16px !important;
  padding: 1.2rem !important;
}}
[data-testid="stFileUploader"], 
[data-testid="stFileUploader"] * {{
  color: white !important;
}}
[data-testid="stFileUploader"] > div,
[data-testid="stFileUploader"] section {{
  background-color: rgba(150,99,104,0.35) !important;
}}
[data-testid="stFileUploader"] button {{
  background: linear-gradient(135deg, #966368, #d69d96) !important;
  color: white !important;
  border-radius: 12px !important;
  border: none !important;
}}

/* ----------------------------
   Input
---------------------------- */
/* Chat input container */
div[data-testid="stChatInput"] {{
    background-color: rgba(255,255,255,0.9) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(150,99,104,0.25) !important;
}}

/* Input interno */
div[data-testid="stChatInput"] textarea {{
    background-color: rgba(255,255,255,0.95) !important;
    color: #4f3b06 !important;
}}

/* Placeholder */
div[data-testid="stChatInput"] textarea::placeholder {{
    color: #966368 !important;
    }}

div[data-testid="stChatInput"] button {{
    background: #966368 !important;
    border-radius: 10px !important;
    border: none !important;
    color: white !important;
}}
[data-testid="stChatMessageContainer"] {{
    background-color: #d69d96 !important;
}}
/* Contenedor del chat completo */
[data-testid="stChatInputContainer"] {{
    background: #d69d96 !important;
}}
/* Barra inferior donde vive el chat */
[data-testid="stBottomBlockContainer"] {{
    background-color: #d69d96 !important;
}}

/* ----------------------------
   Agentes descripción
---------------------------- */
/* Selectbox principal */
div[data-baseweb="select"] > div {{
    background-color: #966368   !important;
    color: white !important;
    border: 1px solid rgba(79,59,6,0.25) !important;
}}

/* Texto dentro */
div[data-baseweb="select"] span {{
    color: #4f3b06 !important;
}}
/* Flecha */
div[data-baseweb="select"] svg {{
    fill: #4f3b06 !important;
}}

/* Menú desplegado */
ul[role="listbox"] {{
    background-color: white !important;
}}

ul[role="listbox"] li {{
    color: #4f3b06 !important;
}}

/* Caja de info */
div[data-testid="stAlert"] {{
    background-color: #966368!important;
    border-left: 6px solid #966368 !important; #!!!!!!!!!!!!!!!!!!!!!!!!!!1111
    color: #966368 !important;
}}

/* Texto dentro */
div[data-testid="stAlert"] p {{
    color: white !important;
}}

/* El contenedor del alert */
div[data-testid="stAlert"]{{
  background: rgba(214,157,150,0.30) !important;   /* rosa suave */
  border-left: 6px solid #966368 !important;
  border-radius: 14px !important;
}}

/* La capa interna 
div[data-testid="stAlert"] > div{{
  background: transparent !important;         
}}

/* A veces Streamlit mete otro wrapper */
div[data-testid="stAlert"] > div > div{{
  background: transparent !important;             /* QUITA la capa */
}}

/* Texto y bullets dentro */
div[data-testid="stAlert"] *{{
  color: white !important;
}}

/* Icono  */
div[data-testid="stAlert"] svg{{
  fill: #4f3b06 !important;
}}

div[data-testid="stAlert"] > div,
div[data-testid="stAlert"] > div > div,
div[role="alert"] > div,
div[role="alert"] > div > div{{
  background: transparent !important;
  box-shadow: none !important;
}}

</style>
    """,
    unsafe_allow_html=True,
)
# ---------------------------
# FUENTES / PDF VIEWER
# ---------------------------
@st.cache_data(ttl=3500)
def get_signed_url(filename: str) -> str:
    try:
        resp = supabase.storage.from_(BUCKET_NAME).create_signed_url(filename, 3600)
        return resp.get("signedURL") or resp.get("signedUrl") or ""
    except Exception:
        return ""


def _render_sources(sources: list):
    if not sources:
        return

    # Agrupar chunks por archivo → páginas únicas
    files: dict = {}
    for s in sources:
        fname = s["file"]
        if fname not in files:
            files[fname] = set()
        files[fname].add(s["page"])

    with st.expander(f"📄 Fuentes consultadas ({len(files)} archivo(s))"):
        for fname, pages in files.items():
            pages_str = ", ".join(f"p.{p}" for p in sorted(pages))
            col_name, col_btn = st.columns([3, 1])
            with col_name:
                st.markdown(f"**{fname}**  \n`{pages_str}`")
            with col_btn:
                url = get_signed_url(fname)
                if url:
                    st.link_button("Ver PDF", url)
                else:
                    st.caption("Sin enlace")


# ---------------------------
# GRÁFICA FINANCIERA
# ---------------------------
def _render_finance_chart(chart_data: dict):
    rows = chart_data.get("table_rows", [])
    numbers = chart_data.get("numbers", {})
    if not rows:
        st.caption("⚠️ No se pudo generar proyección: el contrato no especifica renta mensual.")
        return

    currency = numbers.get("currency") or "MXN"
    total = chart_data.get("total_contract_value", 0)
    max_exp = chart_data.get("max_exposure", 0)
    years = chart_data.get("assumptions", {}).get("years", "?")
    escalation = chart_data.get("assumptions", {}).get("escalation_rate_annual", 0)

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Valor total contrato", f"${total:,.0f} {currency}")
    k2.metric("Renta máxima mensual", f"${max_exp:,.0f} {currency}")
    k3.metric("Horizonte proyectado", f"{years} año(s)")
    k4.metric("Escalación anual", f"{escalation * 100:.1f}%")

    df_proj = pd.DataFrame(rows)

    # Líneas: renta base, variable y total
    has_variable = df_proj["variable_rent"].sum() > 0
    y_cols = ["base_rent", "total"] if not has_variable else ["base_rent", "variable_rent", "total"]
    color_map = {
        "base_rent":     "#966368",
        "variable_rent": "#d1c18a",
        "total":         "#4f3b06",
    }
    name_map = {
        "base_rent":     "Renta base",
        "variable_rent": "Renta variable",
        "total":         "Total",
    }

    fig = px.line(
        df_proj,
        x="month",
        y=y_cols,
        labels={"month": "Mes", "value": f"Monto ({currency})", "variable": ""},
        title="Proyección de flujos del contrato",
        color_discrete_map=color_map,
    )
    fig.for_each_trace(lambda t: t.update(name=name_map.get(t.name, t.name)))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.6)",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=-0.25),
        xaxis=dict(title="Mes", showgrid=False),
        yaxis=dict(title=f"Monto ({currency})", tickformat="$,.0f"),
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver tabla de proyección"):
        st.dataframe(
            df_proj.rename(columns={
                "month": "Mes",
                "base_rent": f"Renta base ({currency})",
                "variable_rent": f"Renta variable ({currency})",
                "total": f"Total ({currency})",
            }),
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------
# SESSION STATE (FIX)
# ---------------------------
if "section" not in st.session_state:
    st.session_state["section"] = "consulta"

if "messages" not in st.session_state:
    st.session_state.messages = []  

if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0

# ---------------------------
# SUPABASE + LLM
# ---------------------------

SUPABASE_URL = "https://lvthchgaspfbuybtrkoe.supabase.co"
SUPABASE_KEY = "sb_secret_Uft6Yv-x6Wf3j7_T5BjniQ_6Bzj-dUC"
BUCKET_NAME = "contratos"

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

bucket = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    bucket = supabase.storage.from_(BUCKET_NAME)
else:
    st.warning("⚠️ Supabase no configurado (SUPABASE_URL / SUPABASE_KEY vacíos). La sección de PDFs/bucket no funcionará.")

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

def list_all_pdfs_in_bucket(prefix: str = "") -> list[str]:
    """
    Lista TODOS los PDFs del bucket (incluyendo subcarpetas).
    Regresa paths tipo: 'Colima/C02_Contrato_Colima-02.pdf'
    """
    if bucket is None:
        return []

    pdfs = []
    stack = [prefix.strip("/")] if prefix else [""]

    while stack:
        cur = stack.pop()
        items = bucket.list(path=cur)

        for it in items or []:
            name = it.get("name", "")
            if not name:
                continue

            # Supabase Storage list() regresa nombres relativos al path consultado
            full = f"{cur}/{name}".strip("/") if cur else name

            # Si es carpeta, la exploramos (en Supabase suele venir sin ".pdf")
            if not name.lower().endswith(".pdf"):
                # heurística simple: si no trae extensión, lo tratamos como folder
                # (si en tu bucket hay archivos sin extensión, dímelo y ajustamos)
                stack.append(full)
                continue

            pdfs.append(full)

    # quita duplicados y ordena
    return sorted(set(pdfs))

def find_codigo_civil_pdf(all_pdfs: list[str]) -> Optional[str]:
    """
    Busca automáticamente el PDF del Código Civil.
    Ajusta las palabras clave según cómo lo tengas guardado.
    """
    preferred_patterns = [
        "codigo civil",
        "código civil",
        "codigo_civil",
        "codigocivil",
    ]

    normalized = []
    for p in all_pdfs:
        base = os.path.basename(p).lower()
        normalized.append((p, base))

    # 1) match preferente por nombre
    for full_path, base in normalized:
        if any(pat in base for pat in preferred_patterns):
            return full_path

    # 2) fallback: buscar en el path completo
    for p in all_pdfs:
        low = p.lower()
        if any(pat in low for pat in preferred_patterns):
            return p

    return None


def unique_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out
# ---------------------------
# Helpers RAG
# --------------------------- 
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
def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def infer_files_from_question(question: str, all_pdfs: list[str]) -> list[str]:
    qn = _norm(question)
    if not qn:
        return []

    scored = []
    for p in all_pdfs:
        base = _norm(os.path.basename(p).replace(".pdf", ""))
        tokens = [t for t in base.split() if len(t) >= 3]

        score = 0
        for t in tokens:
            if t in qn:
                score += 1

        # bonus si menciona algo tipo C02 / C01
        if re.search(r"\bc\d{1,3}\b", qn) and re.search(r"\bc\d{1,3}\b", base):
            if re.search(r"\bc\d{1,3}\b", qn).group(0) in base:
                score += 3

        if score > 0:
            scored.append((score, p))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [p for _, p in scored[:3]]

def embed_texts(texts):
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return np.array([d.embedding for d in resp.data], dtype=np.float32)

def cosine_sim_matrix(a: np.ndarray, b: np.ndarray):
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a_norm @ b_norm.T

@st.cache_resource(show_spinner=True)
def build_index(max_pages: int, chunk_chars: int, overlap: int, files_to_index: Optional[tuple[str, ...]] = None):
    if bucket is None:
        return [], np.zeros((0, 1), dtype=np.float32)

    all_files = list_all_pdfs_in_bucket()
    pdf_files = list(files_to_index) if files_to_index else all_files

    docs, texts = [], []

    for path in pdf_files:
        try:
            pdf_bytes = bucket.download(path)
        except Exception:
            continue

        pages = pdf_bytes_to_pages(pdf_bytes, max_pages)
        for page_num, page_text in pages:
            for ci, chunk in enumerate(chunk_text(page_text, chunk_chars, overlap)):
                docs.append({"file": path, "page": page_num, "chunk": ci, "text": chunk})
                texts.append(chunk)

    if not texts:
        return [], np.zeros((0, 1), dtype=np.float32)

    embs = []
    for i in range(0, len(texts), 64):
        embs.append(embed_texts(texts[i:i + 64]))

    return docs, np.vstack(embs)

def retrieve_context(
    question: str,
    docs,
    doc_embs,
    k: int,
    allowed_files: Optional[set[str]] = None
):
    q_emb = embed_texts([question])
    sims = cosine_sim_matrix(doc_embs, q_emb).reshape(-1)

    idx = np.arange(len(docs))
    if allowed_files:
        mask = np.array([d["file"] in allowed_files for d in docs], dtype=bool)
        idx = idx[mask]
        sims = sims[mask]

    if len(idx) == 0:
        return "", []

    top_local = np.argsort(-sims)[:k]
    top_idx = idx[top_local]

    selected = [docs[int(i)] for i in top_idx]
    context = "\n\n".join(
        [f"Source: {d['file']} (page {d['page']}, chunk {d['chunk']})\n{d['text']}"
         for d in selected]
    )
    return context, selected

def retrieve_context_with_neighbors(
    question: str,
    docs: list[dict],
    doc_embs: np.ndarray,
    k: int,
    allowed_files: Optional[set[str]] = None,
    neighbor_radius: int = 1,
):
    """
    Recupera top-k por embeddings y además agrega vecinos (chunks cercanos)
    para evitar perder la frase exacta que responde.
    SIN keywords. Esto mejora para cualquier pregunta.
    """
    q_emb = embed_texts([question])
    sims = cosine_sim_matrix(doc_embs, q_emb).reshape(-1)

    idx = np.arange(len(docs))
    if allowed_files:
        mask = np.array([d["file"] in allowed_files for d in docs], dtype=bool)
        idx = idx[mask]
        sims = sims[mask]

    top_local = np.argsort(-sims)[:k]
    top_idx = idx[top_local].tolist()

    # Agregar vecinos por (file,page) y chunk +/- radius
    want = set(top_idx)
    # índice rápido: (file,page,chunk)->global_i
    pos2i = {(d["file"], d["page"], d["chunk"]): i for i, d in enumerate(docs)}

    for gi in top_idx:
        d = docs[int(gi)]
        for delta in range(-neighbor_radius, neighbor_radius + 1):
            if delta == 0:
                continue
            key = (d["file"], d["page"], d["chunk"] + delta)
            if key in pos2i:
                want.add(pos2i[key])

    selected = [docs[int(i)] for i in sorted(want)]
    context = "\n\n".join(
        [f"Source: {d['file']} (page {d['page']}, chunk {d['chunk']})\n{d['text']}"
         for d in selected]
    )
    return context, selected


def retrieve_context_fallback(
    question: str,
    docs: list[dict],
    doc_embs: np.ndarray,
    allowed_files: set[str],
    k_primary: int = 6,
    k_fallback: int = 16,
):
    """
    1er intento: k pequeño + vecinos
    Si el contexto es pobre, 2do intento: k más grande + más vecinos
    SIN keywords.
    """
    ctx1, src1 = retrieve_context_with_neighbors(
        question, docs, doc_embs, k=k_primary, allowed_files=allowed_files, neighbor_radius=1
    )

    # Heurística genérica de "contexto pobre": muy corto o muy repetitivo
    too_short = len(ctx1) < 1200
    if not too_short:
        return ctx1, src1

    ctx2, src2 = retrieve_context_with_neighbors(
        question, docs, doc_embs, k=k_fallback, allowed_files=allowed_files, neighbor_radius=2
    )
    return ctx2, src2


def ask_llm_chat(question: str, context: str, history: list, max_turns: int = 30) -> str:
    """
    history: lista de dicts {"role": "user"|"bot", "text": "..."} guardada en session_state
    max_turns: cuántos mensajes previos (pares user/bot) usar como memoria corta
    """

    # tomar solo los últimos mensajes (memoria corta)
    recent = history[-max_turns:] if len(history) > max_turns else history

    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente especializado en análisis de contratos.\n"
                "Responde usando el CONTEXTO recuperado del RAG. Si falta información, di 'No especificado en contrato'.\n"
                "Sé claro, con bullets si ayuda."
            ),
        }
    ]

    # historial (sin contexto viejo)
    for m in recent:
        r = m.get("role", "")
        if r == "user":
            messages.append({"role": "user", "content": m.get("text", "")})
        elif r == "bot":
            messages.append({"role": "assistant", "content": m.get("text", "")})

    # mensaje actual con contexto
    messages.append({
        "role": "user",
        "content": f"CONTEXTO (RAG):\n{context}\n\nPREGUNTA:\n{question}"
    })

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()

def safe_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return name or "upload.bin"

def upload_to_bucket(file_bytes: bytes, dest_path: str, content_type: Optional[str] = None):
    if bucket is None:
        raise RuntimeError("Supabase bucket no configurado.")
    opts = {"content-type": content_type} if content_type else {}
    return bucket.upload(dest_path, file_bytes, file_options=opts)

# ---------------------------
# FUNCIONES DE ALERTAS Y CALENDARIO
# ---------------------------
def alert_date(expiry: date) -> date:
    return expiry - relativedelta(months=3)

def compute_alerts(contracts, today: date):
    alerts = []
    for c in contracts:
        exp = c["expiry"]
        start_alert = alert_date(exp)
        if start_alert <= today <= exp:
            alerts.append({
                **c,
                "alert_start": start_alert,
                "days_left": (exp - today).days
            })
    alerts.sort(key=lambda x: x["days_left"])
    return alerts

def build_calendar_events(contracts):
    events = []
    for c in contracts:
        exp = c["expiry"]
        start_alert = alert_date(exp)

        # extendedProps SOLO con strings/números
        safe_props = {
            "type": "alert",
            "id": str(c.get("id", "")),
            "title": str(c.get("title", "")),
            "state": str(c.get("state", "")),
            "expiry": exp.isoformat(),                 # ✅ string
            "alert_start": start_alert.isoformat(),    # ✅ string
        }

        events.append({
            "title": f"⚠️ Alerta (3m) · {c['id']}",
            "start": start_alert.isoformat(),  # ✅ string
            "allDay": True,
            "extendedProps": safe_props
        })

        safe_props2 = dict(safe_props)
        safe_props2["type"] = "expiry"

        events.append({
            "title": f"⛔ Vence · {c['id']}",
            "start": exp.isoformat(),          # ✅ string
            "allDay": True,
            "extendedProps": safe_props2
        })

    return events

# ---------------------------
# Demo: contratos en memoria
# ---------------------------
if "contracts" not in st.session_state:
    st.session_state.contracts = [
        {"id": "C-001", "title": "Arrendamiento Sucursal Polanco", "state": "Ciudad de México", "expiry": date(2026, 6, 15)},
        {"id": "C-002", "title": "Arrendamiento Bodega Monterrey", "state": "Nuevo León", "expiry": date(2026, 4, 2)},
        {"id": "C-003", "title": "Arrendamiento Oficina Guadalajara", "state": "Jalisco", "expiry": date(2026, 3, 28)},
    ]

today = date.today()
alerts = compute_alerts(st.session_state.contracts, today)

# Notificación dentro de la página (solo cuando está abierta)
if alerts:
    a0 = alerts[0]
    st.toast(f"⏳ '{a0['title']}' vence en {a0['days_left']} días (vence {a0['expiry']})")

# ---------------------------
# SIDEBAR (PROFESIONAL)
# ---------------------------
with st.sidebar:
    st.markdown("### Usuario")
    st.write("👤 CFO / Legal / Ops")
    st.markdown("---")

    if st.button("Consulta", key="consulta_link"):
        st.session_state.section = "consulta"
    if st.button("Subir Documentos", key="sug_link"):
        st.session_state.section = "subir"
    if st.button("Calendario", key="calendario_link"):
        st.session_state.section = "calendario"
    if st.button("Dasboard", key="dashboard_link"):
        st.session_state.section = "dashboard"

# ---------------------------
# TOP BAR
# ---------------------------
active_alerts = len(alerts)
icon = "🟢" if active_alerts == 0 else "🔴"

left, right = st.columns([1.7, 0.9], vertical_alignment="top")
with left:
    st.markdown(
        """
        <div class="topbar">
      <div class="brand">
        <div class="logo"></div>
        <div>
          <div class="brand-title">Asistente Virtual Vertiche</div>
          <div class="brand-sub">Análisis de Contratos</div>
        </div>
      </div>
        """,
        unsafe_allow_html=True,
    )

with right:

    st.markdown(
        f"""
        <div class="kpi-row">
        <div class="kpi">
          <div class="label">Alertas activas</div>
          <div class="value">{active_alerts} {icon}</div>
        </div>
        <div class="kpi">
          <div class="label">Fecha</div>
          <div class="value">{datetime.now().strftime("%d/%m/%y")}</div>
        </div>
      </div>
    </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

def _safe_html_text(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

#txt = _safe_html_text(m.get("text",""))

# ---------------------------
# BODY: Tabs
# ---------------------------
section = st.session_state.section

if section == "consulta":
    # ---------------------------
    # Render messages (burbujas)
    # ---------------------------
    normalized = []
    for m in st.session_state.messages:
        if isinstance(m, dict):
            normalized.append({
                "role": m.get("role", "bot"),
                "text": m.get("text", ""),
                "sources": m.get("sources"),
                "chart_data": m.get("chart_data"),
            })
        else:
            normalized.append({"role": "bot", "text": str(m)})

    st.session_state.messages = normalized

    for m in st.session_state.messages:
        role = m.get("role", "")
        txt = _safe_html_text(m.get("text", ""))

        if role == "user":
            st.markdown(f"""
            <div class="msg" style="justify-content:flex-end;">
              <div class="bubble user">{txt}</div>
              <div class="avatar user"></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="msg" style="justify-content:flex-start;">
              <div class="avatar bot"></div>
              <div class="bubble bot">{txt}</div>
            </div>
            """, unsafe_allow_html=True)

            if m.get("chart_data"):
                _render_finance_chart(m["chart_data"])
            if m.get("sources"):
                _render_sources(m["sources"])

    # ---------------------------
    # Parámetros de consulta
    # ---------------------------
    max_pages = 60
    chunk_chars = 1200
    overlap = 200
    top_k = 12

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

    # ---------------------------
    # PDFs disponibles
    # ---------------------------
    all_pdfs = list_all_pdfs_in_bucket()

    if not all_pdfs:
        st.warning("No se encontraron PDFs en el bucket.")
        st.stop()

    selected_pdf = None
    selected_legal_docs = []

    # ---------------------------
    # Selección de documentos
    # ---------------------------
    if mode == "Por agente" and selected_agent_key == "legal":
        codigo_civil_pdf = find_codigo_civil_pdf(all_pdfs)

        st.markdown("#### Consulta legal multi-documento")

        if not codigo_civil_pdf:
            st.error("No encontré el PDF del Código Civil en el bucket. Renómbralo de forma que incluya 'codigo civil'.")
            st.stop()

        st.text_input(
            "Documento legal obligatorio",
            value=codigo_civil_pdf,
            disabled=True,
        )

        additional_options = [p for p in all_pdfs if p != codigo_civil_pdf]

        selected_extra_docs = st.multiselect(
            "Selecciona 2 documentos adicionales",
            options=additional_options,
            default=[],
            max_selections=2,
            help="Además del Código Civil, elige exactamente 2 documentos para la consulta legal.",
        )

        if len(selected_extra_docs) != 2:
            st.caption("Debes elegir exactamente 2 documentos adicionales.")
        else:
            selected_legal_docs = unique_preserve_order(
                [codigo_civil_pdf] + selected_extra_docs
            )
            st.caption("Fuentes legales activas:")
            for doc in selected_legal_docs:
                st.write(f"- {doc}")

    else:
        selected_pdf = st.selectbox(
            "Documento a consultar",
            options=all_pdfs,
            index=0,
        )
        st.caption(f"Consultando SOLO: {selected_pdf}")

    # ---------------------------
    # Input + Enviar
    # ---------------------------
    question = st.text_input(
        "Pregunta",
        placeholder="Pregunta lo que quieras...",
        label_visibility="collapsed",
        key=f"question_input_{st.session_state.input_counter}",
    )
    ask = st.button("Enviar", use_container_width=False)

    # ---------------------------
    # Botones prompt preestablecidos
    # ---------------------------
    chip_prompts = {
        "📌 Resumen ejecutivo": "Dame un resumen ejecutivo del contrato. Incluye puntos clave, riesgos y próximos pasos.",
        "⚠️ Riesgos operativos": "Identifica riesgos operativos del contrato: mantenimiento, servicios, seguros, penalizaciones y restricciones.",
        "💰 Simulación de pagos": "Simula el flujo de pagos: renta, incrementos, indexaciones y fechas relevantes. Indica supuestos si faltan datos.",
        "✅ Checklist de obligaciones": "Genera un checklist de obligaciones del arrendatario y arrendador con evidencia (cláusulas) si aplica."
    }

    st.markdown('<div class="chips">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    cols = [c1, c2, c3, c4]
    pending_chip_prompt = None
    for (label, prompt), col in zip(chip_prompts.items(), cols):
        with col:
            if st.button(label, key=f"chip_{label}"):
                pending_chip_prompt = prompt
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # Ejecutar consulta
    # ---------------------------
    effective_q = question.strip() if (ask and question.strip()) else pending_chip_prompt
    if effective_q:
        q = effective_q
        st.session_state.messages.append({"role": "user", "text": q})

        chart_data = None
        sources = []
        final_answer = ""

        with st.spinner("Procesando..."):
            # Determinar archivos a consultar
            if mode == "Por agente" and selected_agent_key == "legal":
                if len(selected_legal_docs) != 3:
                    st.warning("Para el agente legal debes consultar el Código Civil + 2 documentos adicionales.")
                    st.stop()

                files_for_query = tuple(selected_legal_docs)
                allowed_files = set(selected_legal_docs)

            else:
                if not selected_pdf:
                    st.warning("Debes seleccionar un documento para consultar.")
                    st.stop()

                files_for_query = (selected_pdf,)
                allowed_files = {selected_pdf}

            # Indexar SOLO los archivos elegidos
            docs, doc_embs = build_index(
                max_pages,
                chunk_chars,
                overlap,
                files_to_index=files_for_query
            )

            if not docs:
                st.error("No se pudieron indexar los documentos seleccionados.")
                st.stop()

            # Retrieval robusto
            context, sources = retrieve_context_fallback(
                q,
                docs,
                doc_embs,
                allowed_files=allowed_files,
                k_primary=top_k,
                k_fallback=16
            )

            # Respuesta
            if mode == "General":
                final_answer = ask_llm_chat(
                    q,
                    context,
                    st.session_state.messages,
                    max_turns=12
                )

            else:
                if selected_agent_key == "legal":
                    from agents.legal import run_legal_agent

                    final_answer = run_legal_agent(
                        question=q,
                        context=context,
                        legal_sources={
                            "codigo_civil": selected_legal_docs[0],
                            "documentos_adicionales": selected_legal_docs[1:],
                        }
                    )

                else:
                    results = run_orchestrator(q, context, agent_key=selected_agent_key)
                    final_answer = "\n\n".join(
                        [f"{k}: {v}" for k, v in results.items()]
                    )

                    if selected_agent_key == "finanzas":
                        numbers = extract_finance_numbers(context)
                        extracted = {
                            "lease_type": "retail" if numbers.get("variable_pct") else "comercial",
                            "rent": {
                                "base_monthly": numbers.get("base_monthly"),
                                "variable_pct_over_sales": numbers.get("variable_pct"),
                                "breakpoint_sales": numbers.get("breakpoint_sales"),
                            },
                        }

                        fin = FinanceInputs(
                            years=int(numbers.get("lease_years") or 3),
                            escalation_rate_annual=(numbers.get("escalation_pct") or 4.0) / 100.0,
                        )

                        chart_data = project_cashflows(extracted, fin)
                        chart_data["numbers"] = numbers

        bot_msg = {"role": "bot", "text": final_answer}

        if sources:
            bot_msg["sources"] = sources

        if chart_data is not None:
            bot_msg["chart_data"] = chart_data

        st.session_state.messages.append(bot_msg)
        st.session_state.input_counter += 1
        st.rerun()


elif section == "subir":
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
        names = [it.get("name") for it in (root_files or []) if it.get("name")]

        if names:
            with st.expander(f"📂 Contratos ({len(names)})", expanded=False):
                st.markdown("\n".join([f"- {n}" for n in sorted(names)]))
        else:
            st.write("No hay archivos en la raíz del bucket.")

    except Exception as e:
        st.error(f"No pude listar archivos: {e}")

elif section == "calendario":
    st.markdown("### Calendario de contratos")
    st.caption("Eventos: inicio de alerta (3 meses antes) y vencimiento del contrato.")

    events = build_calendar_events(st.session_state.contracts)

    options = {
        "initialView": "dayGridMonth",
        "height": 600,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listWeek"
        },
        "eventDisplay": "block",
    }

    cal_state = calendar(
    events=events,
    options=options,
    custom_css="""
    .fc {
        background-color: #ffffff;
        color: #4f3b06;
        font-family: 'Segoe UI', sans-serif;
    }

    .fc-daygrid-day-number {
        color: #4f3b06;
    }
    .fc-col-header-cell {
        background-color: #d1c18a;
        color: #4f3b06;
    }
    .fc-day-today {
        background-color: rgba(214,157,150,0.25) !important;
    }
    .fc-button {
        background-color: #966368 !important;
        border: none !important;
    }
    .fc-button:hover {
        background-color: #d69d96 !important;
    }
    """,
    key="full_contracts_calendar"
)

    # Panel de alertas activas debajo
    st.markdown("#### ⚠️ Alertas activas (ventana 3 meses)")
    if not alerts:
        st.caption("No hay contratos en ventana de alerta.")
    else:
        for a in alerts:
            days = a["days_left"]

            if days < 30:
                bg = "rgba(255,80,80,0.15)"
                border = "#ff4d4d"
            elif days < 60:
                bg = "rgba(255,165,0,0.18)"
                border = "#ff9900"
            else:
                bg = "rgba(214,157,150,0.25)"
                border = "#966368"

            st.markdown(
                f"""
                <div style="
                    background: {bg};
                    border-left: 6px solid {border};
                    padding: 0.8rem;
                    border-radius: 10px;
                    color: #white !important;
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                ">
                ⚠️ <b>{a['title']}</b> · vence <b>{a['expiry']}</b> · faltan <b>{a['days_left']}</b> días
                </div>
                """,
                unsafe_allow_html=True
            )

elif section == "dashboard":
    st.markdown("### Dashboard ")

    # ----------------------------
    # Datos (demo) — reemplaza por tu dataset
    # ----------------------------
    df = pd.DataFrame({
        "state": [
            "Aguascalientes","Baja California","Baja California Sur","Campeche","Chiapas","Chihuahua",
            "Ciudad de México","Coahuila","Colima","Durango","Guanajuato","Guerrero","Hidalgo","Jalisco",
            "México","Michoacán","Morelos","Nayarit","Nuevo León","Oaxaca","Puebla","Querétaro",
            "Quintana Roo","San Luis Potosí","Sinaloa","Sonora","Tabasco","Tamaulipas","Tlaxcala",
            "Veracruz","Yucatán","Zacatecas"
        ],
        "count": [4,12,3,2,7,8,18,6,1,3,9,5,4,11,14,6,3,2,13,7,10,5,6,4,8,9,3,5,2,12,4,3]
    })

    # ----------------------------
    # KPI Row
    # ----------------------------
    total = int(df["count"].sum())
    mx = int(df["count"].max())
    mn = int(df["count"].min())
    avg = float(df["count"].mean())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", f"{total}")
    c2.metric("Máximo", f"{mx}")
    c3.metric("Mínimo", f"{mn}")
    c4.metric("Promedio", f"{avg:.1f}")

    st.write("")

    # ----------------------------
    # GeoJSON (cache)
    # ----------------------------
    @st.cache_data
    def load_mexico_geojson():
        url = "https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json"
        return requests.get(url, timeout=20).json()

    mex_geo = load_mexico_geojson()

    # ----------------------------
    # Mapa limpio
    # ----------------------------
    fig = px.choropleth(
        df,
        geojson=mex_geo,
        locations="state",
        featureidkey="properties.name",
        color="count",
        hover_name="state",
        hover_data={"count": True, "state": False},
        color_continuous_scale="Sunset",
    )

    # Layout minimalista (sin márgenes, fondo transparente)
    fig.update_geos(
        fitbounds="locations",
        visible=False
    )
    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title="",
            thickness=10,
            len=0.55,
            outlinewidth=0,
            tickfont=dict(size=11),
        )
    )

    # ----------------------------
    # Dashboard layout: Mapa + ranking
    # ----------------------------
    left, right = st.columns([1.65, 1])

    with left:
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Top 10 estados")
        top10 = df.sort_values("count", ascending=False).head(10)

        # Bar chart minimalista (misma escala)
        bar = px.bar(
            top10[::-1],  # para que el top esté arriba visualmente
            x="count",
            y="state",
            orientation="h",
            text="count",
        )
        bar.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Conteo: %{x}<extra></extra>"
        )
        bar.update_layout(
            height=560,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="", showgrid=False, zeroline=False),
            yaxis=dict(title="", showgrid=False),
        )

        st.plotly_chart(bar, use_container_width=True)

    #with st.expander("Ver tabla completa"):
    #    st.dataframe(df.sort_values("count", ascending=False), use_container_width=True)

# Footer
st.markdown('<div class="footer">© Vertiche  · Tecnológico de Monterrey CEM  </div>', unsafe_allow_html=True)
st.markdown('<div class="footer"> · Ximena Serna Mendoza · Tamara Alejandra Ortiz Villareal · Nathan Isaac García Larios · Mauricio Aguilar Pacheco · </div>', unsafe_allow_html=True)

