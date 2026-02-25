import json
from langchain_core.prompts import ChatPromptTemplate
from core.prompts import EXTRACTOR_SYSTEM

def extract_base(llm, retrieved_context: str, lease_type: str) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACTOR_SYSTEM),
        ("user",
         "Tipo de arrendamiento: {lease_type}\n\n"
         "Contexto del contrato (fragmentos):\n{ctx}\n\n"
         "Extrae el JSON completo con las secciones definidas.")
    ])
    msg = prompt.format_messages(ctx=retrieved_context, lease_type=lease_type)
    raw = llm.invoke(msg).content
    return json.loads(raw)
