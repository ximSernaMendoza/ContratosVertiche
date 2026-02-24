import json
from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, END

from core.llm import get_llm
from core.rag import get_retriever
from agents.router import route_lease_type
from agents.extractor import extract_base
from agents.legal import legal_review
from agents.ops import ops_review
from agents.tax_mx import tax_review
from agents.finance_agent import finance_review

from core.finance import FinanceInputs, project_cashflows
from core.scoring import risk_score
from core.calendar import build_calendar

class LeaseState(TypedDict):
    question: str
    contract_hint: str
    retrieved_context: str
    lease_type: str
    extracted: Dict[str, Any]
    legal: Dict[str, Any]
    finance: Dict[str, Any]
    ops: Dict[str, Any]
    tax: Dict[str, Any]
    score: Dict[str, Any]
    projection: Dict[str, Any]
    calendar: Any
    executive_summary: str

def node_retrieve(state: LeaseState, retriever):
    q = state["question"] or "Resumen del contrato y cláusulas clave"
    docs = retriever.get_relevant_documents(q)
    ctx = "\n\n".join([d.page_content for d in docs])
    state["retrieved_context"] = ctx
    state["contract_hint"] = ctx[:1800]
    return state

def node_route(state: LeaseState, llm):
    state["lease_type"] = route_lease_type(llm, state["contract_hint"])
    return state

def node_extract(state: LeaseState, llm):
    state["extracted"] = extract_base(llm, state["retrieved_context"], state["lease_type"])
    state["extracted"]["lease_type"] = state["lease_type"]
    return state

def node_legal(state: LeaseState, llm):
    state["legal"] = legal_review(llm, state["retrieved_context"], state["extracted"])
    return state

def node_finance(state: LeaseState, llm):
    state["finance"] = finance_review(llm, state["retrieved_context"], state["extracted"])
    return state

def node_ops(state: LeaseState, llm):
    state["ops"] = ops_review(llm, state["retrieved_context"], state["extracted"])
    return state

def node_tax(state: LeaseState, llm):
    state["tax"] = tax_review(llm, state["retrieved_context"], state["extracted"])
    return state

def node_score_calendar_projection(state: LeaseState):
    state["score"] = risk_score(state["extracted"], state["legal"])
    state["calendar"] = build_calendar(state["extracted"])

    # Proyección deterministic (si retail, puedes pasar ventas desde UI)
    fin = FinanceInputs(years=5, monthly_sales=None, escalation_rate_annual=0.04)
    state["projection"] = project_cashflows(state["extracted"], fin)
    return state

def node_exec_summary(state: LeaseState, llm):
    # Resumen ejecutivo final (puede ser LLM, pero corto)
    prompt = (
        "Genera un resumen ejecutivo (máx 12 bullets) para CFO/Legal/Operaciones.\n"
        f"Tipo: {state['lease_type']}\n"
        f"Riesgo: {state['score']}\n"
        f"Hallazgos legales: {json.dumps(state['legal'].get('findings', [])[:5], ensure_ascii=False)}\n"
        f"Finanzas: {json.dumps(state['projection'], ensure_ascii=False)}\n"
        "Devuelve solo texto."
    )
    state["executive_summary"] = llm.invoke(prompt).content
    return state

def build_workflow(retriever):
    llm = get_llm()

    g = StateGraph(LeaseState)
    g.add_node("retrieve", lambda s: node_retrieve(s, retriever))
    g.add_node("route",    lambda s: node_route(s, llm))
    g.add_node("extract",  lambda s: node_extract(s, llm))
    g.add_node("legal",    lambda s: node_legal(s, llm))
    g.add_node("finance",  lambda s: node_finance(s, llm))
    g.add_node("ops",      lambda s: node_ops(s, llm))
    g.add_node("tax",      lambda s: node_tax(s, llm))
    g.add_node("post",     node_score_calendar_projection)
    g.add_node("summary",  lambda s: node_exec_summary(s, llm))

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "route")
    g.add_edge("route", "extract")

    # paralelizable conceptualmente, aquí secuencial simple
    g.add_edge("extract", "legal")
    g.add_edge("legal", "finance")
    g.add_edge("finance", "ops")
    g.add_edge("ops", "tax")
    g.add_edge("tax", "post")
    g.add_edge("post", "summary")
    g.add_edge("summary", END)

    return g.compile()

def run_pipeline(retriever, question: str) -> dict:
    app = build_workflow(retriever)
    init: LeaseState = {
        "question": question,
        "contract_hint": "",
        "retrieved_context": "",
        "lease_type": "",
        "extracted": {},
        "legal": {},
        "finance": {},
        "ops": {},
        "tax": {},
        "score": {},
        "projection": {},
        "calendar": [],
        "executive_summary": ""
    }
    return app.invoke(init)
