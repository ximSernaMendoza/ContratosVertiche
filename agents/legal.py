# agents/legal.py
from openai import OpenAI

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

LEGAL_SYSTEM_PROMPT = """
Eres un abogado experto en contratos de arrendamiento comercial en México.
Respondes SOLO con base en el contexto que se te proporciona.
Enfócate en:
- Cláusulas abusivas
- Terminación unilateral
- Penalidades desproporcionadas
- Responsabilidad por daños estructurales
- Obligaciones de mantenimiento
- Cesión o subarrendamiento
- Renovación automática
- Jurisdicción inconveniente
- Contradicciones entre anexos

Si falta información en el contexto, dilo explícitamente.
"""


def run_legal_agent(question: str, context: str) -> str:
    """
    Agente Legal: analiza el contrato usando el contexto RAG y la pregunta del usuario.
    """
    user_msg = f"""
CONTRATO (fragmentos relevantes):

{context}

PREGUNTA DEL USUARIO:
{question}

Instrucciones:
1. Identifica riesgos en las categorías mencionadas.
2. Explica por qué son riesgos.
3. Cita el texto exacto del contrato cuando sea posible.
4. Si algo importante no aparece en el contexto, menciónalo como posible omisión.
"""
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""