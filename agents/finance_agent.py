from openai import OpenAI
import json

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

FINANCE_SYSTEM_PROMPT = """
Eres un analista financiero de contratos.

REGLAS:
- Usa SOLO el CONTEXTO. No inventes.
- NO uses JSON, NO código, NO listas clave:valor.
- NO copies texto largo del contrato. Citas MÁXIMO 1 oración (<=25 palabras) por punto.
- Si falta info, dilo.

ENTREGA un informe breve con 5 secciones y límites estrictos:

1) Resumen financiero (máx 120 palabras):
   renta fija, moneda, periodicidad, si hay renta variable, mínimos/máximos, costos, inversión inicial, tasa si existe.

2) Ajustes/Indexación (máx 80 palabras):
   INPC/CPI, periodicidad, desde cuándo aplica.

3) Renta variable (máx 80 palabras):
   fórmula, base (ventas/ingresos), límites.

4) Faltantes para modelar flujos (lista corta, máx 8 bullets):
   fechas inicio/fin, tasa descuento, inflación, driver variable, etc.

5) Evidencia (máx 6 bullets):
   cada bullet: Archivo, pág, chunk y una cita corta (<=25 palabras).
"""

def run_financial_agent(question: str, context: str) -> str:
    """
    Agente Financiero (Extractor):
    - Lee el contexto RAG (fragmentos del contrato)
    """
    user_msg = f"""
CONTRATO (fragmentos relevantes):

{context}

PREGUNTA DEL USUARIO:
{question}

Instrucciones:
1) Analiza las condiciones económicas del contrato.
2) Redacta el informe en lenguaje natural profesional.
3) Cita el archivo, página y fragmento textual relevante como evidencia.
4) Si falta información importante para un modelo financiero, indícalo claramente en el apartado correspondiente.
"""
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""