from openai import OpenAI

from config.settings import SETTINGS


client = SETTINGS.get_openai_client()

LEGAL_SYSTEM_PROMPT = """
Eres un abogado experto en contratos de arrendamiento comercial en México.

Tu tarea es analizar de forma jurídica y profesional un contrato de arrendamiento,
comparándolo con:
1) el Código Civil Federal, y
2) el Código Civil del Estado seleccionado.

Reglas obligatorias:
- Responde SOLO con base en la información proporcionada.
- NO inventes artículos, cláusulas, hechos ni conclusiones.
- Distingue con claridad entre:
  a) lo que dice el contrato,
  b) lo que dice el Código Civil Federal,
  c) lo que dice el Código Civil Estatal.
- Si falta evidencia suficiente, dilo expresamente.
- Si una conclusión depende solo del contrato, dilo.
- Si una conclusión depende solo del código estatal o del federal, dilo.
- Si hay contradicción entre contrato y norma, señálala como riesgo legal.
- Prioriza el Código Civil Estatal cuando el contrato se rija por legislación local.
- Usa el Código Civil Federal como marco complementario y de apoyo interpretativo.

Debes analizar con especial atención:
- cláusulas abusivas,
- penalidades desproporcionadas,
- rescisión o terminación anticipada,
- intereses moratorios,
- depósitos o garantías excesivas,
- obligaciones de mantenimiento,
- cesión o subarrendamiento,
- jurisdicción y ley aplicable,
- renovación o prórroga,
- restricciones excesivas al arrendatario,
- contradicciones entre cláusulas,
- omisiones relevantes.

Formato obligatorio de respuesta:
1. Resumen ejecutivo
2. Hallazgos jurídicos relevantes
3. Comparación contrato vs código estatal
4. Comparación contrato vs código federal
5. Riesgos legales detectados
6. Conclusión

Cada hallazgo debe indicar, cuando sea posible:
- cláusula o parte del contrato,
- base legal,
- explicación,
- nivel de riesgo: ALTO / MEDIO / BAJO.
"""

def run_legal_agent(
    question: str,
    contract_full_text: str,
    federal_context: str,
    state_context: str,
    legal_sources: dict | None = None,
) -> str:
    """
    Agente legal especializado.

    Parámetros:
        question: pregunta del usuario
        contract_full_text: texto completo del contrato seleccionado
        federal_context: fragmentos relevantes del Código Civil Federal
        state_context: fragmentos relevantes del Código Civil Estatal
        legal_sources:
            {
                "codigo_federal": "ruta/pdf_federal.pdf",
                "codigo_estatal": "ruta/pdf_estatal.pdf",
                "contrato": "ruta/contrato.pdf"
            }
    """
    legal_sources = legal_sources or {}

    codigo_federal = legal_sources.get("codigo_federal", "No especificado")
    codigo_estatal = legal_sources.get("codigo_estatal", "No especificado")
    contrato = legal_sources.get("contrato", "No especificado")

    # recortes defensivos para evitar exceso de tokens
    max_contract_chars = 30000
    max_context_chars = 12000

    safe_contract = (contract_full_text or "")[:max_contract_chars]
    safe_federal_context = (federal_context or "")[:max_context_chars]
    safe_state_context = (state_context or "")[:max_context_chars]

    user_msg = f"""
FUENTES JURÍDICAS UTILIZADAS:
1. Código Civil Federal:
- {codigo_federal}

2. Código Civil Estatal:
- {codigo_estatal}

3. Contrato analizado:
- {contrato}

CONTRATO COMPLETO (fuente principal de hechos y cláusulas):
{safe_contract}

CÓDIGO CIVIL ESTATAL (fragmentos relevantes recuperados):
{safe_state_context}

CÓDIGO CIVIL FEDERAL (fragmentos relevantes recuperados):
{safe_federal_context}

PREGUNTA DEL USUARIO:
{question}

INSTRUCCIONES ESPECÍFICAS:
1. Analiza primero el contrato completo.
2. Identifica las cláusulas relevantes para responder la pregunta.
3. Después compara esas cláusulas contra el Código Civil Estatal.
4. Usa el Código Civil Federal como apoyo complementario.
5. No digas que una cláusula es abusiva solo por sonar severa; explica jurídicamente por qué puede ser riesgosa, desproporcionada, ambigua o contraria al marco normativo proporcionado.
6. Si una respuesta no puede sostenerse con evidencia textual del contrato o de los códigos, dilo expresamente.
7. Cita o parafrasea con precisión lo que aparece en el contrato y en los códigos.
8. Distingue claramente entre:
   - evidencia contractual,
   - evidencia del código estatal,
   - evidencia del código federal.
9. Si detectas una posible contradicción, explícalo con claridad.
10. Sé técnico, claro y profesional, como un abogado junior especializado en arrendamiento comercial.

IMPORTANTE:
- El contrato debe tratarse como documento principal.
- El Código Civil Estatal debe tratarse como referencia normativa principal local.
- El Código Civil Federal debe tratarse como referencia complementaria.
"""

    try:
        resp = client.chat.completions.create(
            model=SETTINGS.CHAT_MODEL,
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
            "que el modelo cargado coincida con CHAT_MODEL y que los textos enviados no sean demasiado grandes."
        )