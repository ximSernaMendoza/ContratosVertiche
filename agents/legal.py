# agents/legal.py
from openai import OpenAI

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

LEGAL_SYSTEM_PROMPT = """
Eres un abogado experto en contratos de arrendamiento comercial en México.
Respondes SOLO con base en el contexto que se te proporciona.
Debes analizar el contexto como un conjunto de fuentes jurídicas y contractuales.

Prioridades:
- Usa el Código Civil como fuente normativa obligatoria cuando esté presente.
- Usa los documentos adicionales como evidencia contractual o complementaria.
- Distingue entre norma legal, cláusula contractual y comentario analítico.
- Si hay contradicción entre contrato y norma, señálala como riesgo legal.

Enfócate en:
- Cláusulas abusivas
- Terminación unilateral
- Penalidades desproporcionadas
- Responsabilidad por daños estructurales
- Obligaciones de mantenimiento
- Cesión o subarrendamiento
- Renovación automática
- Jurisdicción inconveniente
- Contradicciones entre anexos o entre documentos

Si falta información en el contexto, dilo explícitamente.
No inventes artículos, cláusulas ni conclusiones.

"""


def run_legal_agent(question: str, context: str, legal_sources: dict | None = None) -> str:
    """
    Agente Legal: analiza el contrato usando contexto RAG multi-documento.
    legal_sources:
        {
            "codigo_civil": "ruta/pdf.pdf",
            "documentos_adicionales": ["doc1.pdf", "doc2.pdf"]
        }
    """
    legal_sources = legal_sources or {}
    codigo_civil = legal_sources.get("codigo_civil", "No especificado")
    docs_extra = legal_sources.get("documentos_adicionales", [])

    docs_extra_text = "\n".join([f"- {d}" for d in docs_extra]) if docs_extra else "- Ninguno"

    # recorte defensivo del contexto para evitar errores por exceso de tokens
    max_context_chars = 18000
    safe_context = context[:max_context_chars] if context else ""
    
    user_msg = f"""
FUENTES CONSULTADAS:
1. Código Civil (obligatorio):
- {codigo_civil}

2. Documentos adicionales:
{docs_extra_text}

CONTEXTO RECUPERADO (fragmentos relevantes de las fuentes):
{safe_context}

PREGUNTA DEL USUARIO:
{question}

Instrucciones:
1. Analiza la pregunta con enfoque jurídico.
2. Usa el Código Civil como referencia normativa obligatoria cuando aplique.
3. Identifica riesgos en las categorías mencionadas.
4. Explica por qué son riesgos.
5. Usa los otros documentos como apoyo contractual, comparación o evidencia complementaria.
6. Distingue claramente entre:
   - lo que dice el contrato / documento específico,
   - lo que establece el Código Civil,
   - y cualquier contradicción o riesgo entre ambos.
7. Cita el texto exacto del contexto cuando sea posible.
8. Si una conclusión depende solo del Código Civil, indícalo expresamente.
9. Si una conclusión depende solo del contrato, indícalo expresamente.
10. Si no hay evidencia suficiente en el contexto, menciónalo como posible omisión.
"""
    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
        )
        return (resp.choices[0].message.content or "").strip()

    except Exception as e:
        return (
            "Error al consultar el agente legal.\n\n"
            f"Detalle técnico: {type(e).__name__}: {e}\n\n"
            "Verifica que LM Studio esté abierto, que el servidor local esté activo, "
            "que el modelo cargado coincida con CHAT_MODEL y que el contexto no sea demasiado grande."
        )