import os
import re
import numpy as np
import streamlit as st
import fitz
from supabase import create_client
from openai import OpenAI
from agents.router import run_orchestrator, list_agents
import streamlit as st
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import requests
from dateutil.relativedelta import relativedelta
from streamlit_calendar import calendar
from typing import Optional


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
        flex: 1 1 180px;
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
        margin: .75rem 0 0 0;
      }}
      .chip {{
        padding: .45rem .7rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.55);
        border: 1px solid rgba(79,59,6,0.14);
        color: var(--brown-main);
        font-weight: 600;
        font-size: .85rem;
        cursor: default;
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
        background: linear-gradient(135deg, rgba(150,99,104,0.95), rgba(214,157,150,0.95)) !important;
        color: white !important;
        font-weight: 700 !important;
        padding: .55rem .9rem !important;
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

    </style>
    """,
    unsafe_allow_html=True,
)
# ---------------------------
# SESSION STATE (FIX)
# ---------------------------
if "section" not in st.session_state:
    st.session_state["section"] = "consulta"

if "messages" not in st.session_state:
    st.session_state.messages = []  

# ---------------------------
#

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
    if bucket is None:
        return [], np.zeros((0, 1), dtype=np.float32)

    files = bucket.list(path="")
    pdf_files = [f["name"] for f in files if f.get("name", "").lower().endswith(".pdf")]
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

left, right = st.columns([1.7, 1], vertical_alignment="top")
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

# ---------------------------
# BODY: Tabs
# ---------------------------
section = st.session_state.section

if section == "consulta":
    # ---------------------------
    # Render messages (burbujas)
    # ---------------------------
    for m in st.session_state.messages:
        role = m["role"]
        txt = m["text"]

        if role == "user":
            st.markdown(
                f"""
                <div class="msg" style="justify-content:flex-end;">
                  <div class="bubble user">{txt}</div>
                  <div class="avatar user"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="msg" style="justify-content:flex-start;">
                  <div class="avatar bot"></div>
                  <div class="bubble bot">{txt}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ---------------------------
    # Parámetros de consulta (fijos)
    # ---------------------------
    max_pages = 60
    chunk_chars = 1200
    overlap = 200
    top_k = 6

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
    # Input + Enviar (sin label vacío)
    # ---------------------------
    question = st.text_input(
        "Pregunta",
        placeholder="Pregunta lo que quieras...",
        label_visibility="collapsed",
        key="question_input",
    )
    ask = st.button("Enviar", use_container_width=False)

    # ---------------------------
    # Ejecutar consulta
    # ---------------------------
    if ask and question.strip():
        q = question.strip()

        # Guardar mensaje del usuario
        st.session_state.messages.append({"role": "user", "text": q})

        with st.spinner("Procesando..."):
            docs, doc_embs = build_index(max_pages, chunk_chars, overlap)
            if not docs:
                st.error("No PDFs found")
                st.stop()

            context, sources = retrieve_context(q, docs, doc_embs, top_k)

            if mode == "General":
                final_answer = ask_llm(q, context)
            else:
                results = run_orchestrator(q, context, agent_key=selected_agent_key)
                # Unir respuestas en un solo texto para el chat
                final_answer = "\n\n".join([f"{k}: {v}" for k, v in results.items()])

        # Guardar respuesta del bot
        st.session_state.messages.append({"role": "bot", "text": final_answer})

        # (Opcional) limpiar input
        st.session_state["question_input"] = ""

    # ---------------------------
    # Chips (solo UI)
    # ---------------------------
    st.markdown(
        """
        <div class="chips">
          <div class="chip">📌 Resumen ejecutivo</div>
          <div class="chip">⚠️ Riesgos operativos</div>
          <div class="chip">💰 Simulación de pagos</div>
          <div class="chip">✅ Checklist de obligaciones</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------
    # (Opcional) Bottom bar (solo UI visual)
    # OJO: si la usas, NO pongas inputs duplicados aquí
    # ---------------------------
    st.markdown(
        """
        <div class="bottom-bar">
          <div class="bottom-inner">
            <div class="hint">Escribe tu pregunta arriba y presiona Enviar</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        if root_files:
            for it in root_files:
                st.write(f"- {it.get('name')}")
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
            st.warning(f"**{a['title']}** · vence **{a['expiry']}** · faltan **{a['days_left']}** días")

elif section == "dashboard":
    st.markdown("### Dashboard ")

    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import requests

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
    # Escala de color — ELIGE UNA
    # ----------------------------
    # Opción A: escala de Plotly bonita y moderna
    color_scale = "Sunset"     # otras buenas: "Reds", "Peach", "Aggrnyl", "Viridis"

    # Opción B: escala personalizada con tu paleta (beige -> rosa -> rosa oscuro)
    custom_scale = [
        [0.0, "#d1c18a"],  # beige
        [0.5, "#d69d96"],  # rosa claro
        [1.0, "#966368"],  # rosa oscuro
    ]
    # Si quieres la personalizada, descomenta esta línea:
    # color_scale = custom_scale

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
        color_continuous_scale=color_scale,
    )

    # Tooltip limpio (menos “basura”)
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Conteo: %{z}<extra></extra>",
        marker_line_width=0.6,
        marker_line_color="rgba(255,255,255,0.65)"  # borde sutil
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
