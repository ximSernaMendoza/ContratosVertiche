import json
import re
from openai import OpenAI

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

EXTRACTION_PROMPT = """Extrae los datos financieros del contrato de arrendamiento del CONTEXTO.
Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown.

{
  "base_monthly": <renta mensual fija como número o null>,
  "currency": "<MXN|USD|UDIS o null>",
  "escalation_pct": <porcentaje anual de incremento como número, ej: 4.5, o null>,
  "lease_years": <duración del contrato en años como número o null>,
  "variable_pct": <porcentaje sobre ventas como número o null>,
  "breakpoint_sales": <monto de ventas umbral para renta variable o null>,
  "deposit_months": <meses de depósito en garantía como número o null>
}

Si un campo no aparece explícito en el contexto, usa null. No inventes valores."""


def extract_finance_numbers(context: str) -> dict:
    """Extrae campos financieros clave del contexto RAG como JSON estructurado."""
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"CONTEXTO:\n{context}"},
        ],
        temperature=0.0,
    )
    raw = resp.choices[0].message.content or "{}"
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}

FINANCE_SYSTEM_PROMPT = """
Eres un analista financiero de contratos. Tu trabajo es EXTRAER y RESUMIR condiciones económicas con evidencia.

REGLAS CRÍTICAS:
- Usa SOLO el CONTEXTO proporcionado. No inventes, no supongas, no completes con conocimiento general.
- Si un dato no aparece explícito, escribe: "No se especifica en el contexto".
- Si el contexto tiene datos contradictorios (p.ej. dos montos distintos), NO elijas uno: reporta "Conflicto en el contexto" y muestra ambas evidencias.
- NO uses JSON. NO uses código. NO uses listas tipo clave:valor. NO uses tablas.
- NO copies texto largo. Máximo 1 cita por bullet y la cita debe tener <=25 palabras.
- No agregues secciones extra. Usa EXACTAMENTE los encabezados y el orden de abajo.
- En cada afirmación que contenga un número (monto, % , fechas, moneda, periodicidad, índice), incluye al final una referencia corta: (Archivo, pX, chY).

FORMATO DE ENTRADA:
El CONTEXTO contiene fragmentos con su fuente en líneas tipo:
"Source: <archivo> (page <n>, chunk <m>)"
Usa esos metadatos para tus referencias.

FORMATO DE SALIDA (OBLIGATORIO, exactamente 5 secciones):

1) Resumen financiero (máx 120 palabras)
- Resume renta fija (si existe), moneda, periodicidad, condiciones de pago, mínimos/máximos, costos adicionales, inversión inicial, tasas/intereses si existen.
- Si algo falta, dilo explícitamente.

2) Ajustes/Indexación (máx 80 palabras)
- Describe si hay INPC/CPI/u otro índice, periodicidad, desde cuándo aplica, fórmula o regla si aparece.
- Si no existe, dilo.

3) Renta variable (máx 80 palabras)
- Describe si existe componente variable, base (ventas/ingresos/u otra), fórmula/regla, límites o topes.
- Si no existe, dilo.

4) Faltantes para modelar flujos (máx 8 bullets)
- Lista variables que un modelo necesita y NO están explícitas en el contexto (p.ej. fecha inicio/fin, calendario de pagos, tasa descuento, inflación, base variable, impuestos, tipo de cambio, penalizaciones, etc.).
- Cada bullet debe ser corto y accionable.

5) Evidencia (máx 6 bullets)
- Cada bullet debe seguir EXACTAMENTE este formato:
  Archivo | p<n> | ch<m> | "<cita>"
- La cita debe apoyar un punto clave de las secciones 1-3.
- La cita debe tener <=25 palabras.
"""

def run_financial_agent(question: str, context: str) -> str:
    """
    Agente Financiero (Extractor):
    - Lee el contexto RAG (fragmentos del contrato)
    """
    user_msg = f"""
CONTEXTO (fragmentos con Source):

{context}

PREGUNTA:
{question}

Tarea:
- Produce el informe con las 5 secciones y respeta límites.
- No inventes. Si falta info: "No se especifica en el contexto".
"""
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": FINANCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
    )
    return resp.choices[0].message.content or ""