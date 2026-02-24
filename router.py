from langchain_core.prompts import ChatPromptTemplate
from core.prompts import ROUTER_SYSTEM

def route_lease_type(llm, contract_hint: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", ROUTER_SYSTEM),
        ("user", "Texto (resumen o fragmentos):\n{t}")
    ])
    out = llm.invoke(prompt.format_messages(t=contract_hint)).content.strip().lower()
    if out not in {"habitacional","comercial","industrial","retail"}:
        return "comercial"
    return out
