import os, uuid, tempfile, json
import streamlit as st
from dotenv import load_dotenv

from core.rag import build_vectorstore_from_pdf, get_retriever
from core.pipeline import run_pipeline
from core.finance import FinanceInputs, project_cashflows

load_dotenv()

st.set_page_config(page_title="Lease AI (Multi-Agente + RAG)", layout="wide")

st.title("📄 Lease AI — Multi-Agente (Legal/Finanzas/Ops/Fiscal) + RAG")
st.caption("Sube un contrato de arrendamiento (PDF) y conversa con el asistente para análisis auditable.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "retriever" not in st.session_state:
    st.session_state.retriever = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "messages" not in st.session_state:
    st.session_state.messages = [{"role":"assistant","content":"Sube un PDF y dime qué quieres analizar (p.ej. riesgos, proyección 5 años, redlines, calendario)."}]

with st.sidebar:
    st.header("⚙️ Configuración")
    chroma_dir = os.getenv("CHROMA_DIR", "./chroma_db")
    st.write(f"Chroma dir: `{chroma_dir}`")

    uploaded = st.file_uploader("Sube contrato (PDF)", type=["pdf"])
    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(uploaded.read())
            pdf_path = f.name

        collection = f"lease_{st.session_state.session_id}"
        vs = build_vectorstore_from_pdf(pdf_path, persist_dir=chroma_dir, collection_name=collection)
        st.session_state.retriever = get_retriever(vs, k=6)
        st.success("✅ PDF indexado en RAG (Chroma). Ya puedes preguntar.")

    st.divider()
    st.subheader("🛍 Retail: escenario de ventas")
    monthly_sales = st.number_input("Ventas mensuales (MXN) para renta variable", min_value=0.0, value=0.0, step=10000.0)
    years = st.slider("Horizonte de proyección (años)", 1, 10, 5)

# Chat UI
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_q = st.chat_input("Pregunta (ej. 'haz análisis completo', 'dame redlines', 'proyección 10 años', 'banderas rojas')")

if user_q:
    st.session_state.messages.append({"role":"user","content":user_q})
    with st.chat_message("user"):
        st.markdown(user_q)

    if st.session_state.retriever is None:
        with st.chat_message("assistant"):
            st.error("Primero sube un PDF para habilitar RAG.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Analizando con agentes (Legal/Finanzas/Ops/Fiscal) + RAG..."):
                result = run_pipeline(st.session_state.retriever, question=user_q)

                # Si retail y el usuario dio ventas, recalcula proyección deterministic:
                try:
                    extracted = result.get("extracted", {})
                    if extracted.get("lease_type") == "retail" and monthly_sales > 0:
                        fin = FinanceInputs(years=years, monthly_sales=monthly_sales, escalation_rate_annual=0.04)
                        result["projection"] = project_cashflows(extracted, fin)
                except Exception:
                    pass

                st.session_state.last_result = result

                st.markdown("### ✅ Resumen ejecutivo")
                st.write(result.get("executive_summary","(sin resumen)"))

                st.markdown("### 🧭 Riesgo total")
                score = result.get("score", {})
                st.metric("Score (0–100)", score.get("total_score_0_100", 0), score.get("level",""))

        st.session_state.messages.append({"role":"assistant","content":"Listo. Revisa las pestañas (Extracción/Legal/Finanzas/Ops/Fiscal/Calendario). Si quieres, puedo generar redlines o un reporte tipo CFO."})

if st.session_state.last_result:
    r = st.session_state.last_result
    tabs = st.tabs(["Extracción JSON", "Legal", "Finanzas", "Operaciones", "Fiscal (MX)", "Calendario", "Riesgo", "Proyección"])

    with tabs[0]:
        st.json(r.get("extracted", {}))

    with tabs[1]:
        st.json(r.get("legal", {}))

    with tabs[2]:
        st.json(r.get("finance", {}))

    with tabs[3]:
        st.json(r.get("ops", {}))

    with tabs[4]:
        st.json(r.get("tax", {}))

    with tabs[5]:
        st.json(r.get("calendar", []))

    with tabs[6]:
        st.json(r.get("score", {}))

    with tabs[7]:
        st.json(r.get("projection", {}))
