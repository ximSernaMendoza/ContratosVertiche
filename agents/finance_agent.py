from openai import OpenAI
import json

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

FINANCE_SYSTEM_PROMPT = """
Devuelve EXCLUSIVAMENTE un JSON válido.
No uses markdown.
No agregues texto antes ni después del JSON.
No expliques nada fuera del JSON.

Eres un asistente financiero especializado en análisis de contratos.
Tu tarea es EXTRAER datos financieros estructurados desde el CONTEXTO proporcionado (fragmentos de PDFs).

REGLAS CRÍTICAS:
1) Usa SOLO información explícita en el CONTEXTO.
2) NO inventes valores.
3) Si un dato no está explícitamente presente, usa null y agrégalo en "missing_fields".
4) Si una fecha no está claramente definida, NO la infieras.
5) Fechas deben estar en formato ISO: YYYY-MM-DD.
6) Tasas deben estar en formato decimal (ejemplo: 0.12 para 12%).
7) Montos deben ser numéricos (sin símbolos de moneda).
8) Si el contrato habla de plazo (ej: 36 meses) pero no fecha inicio, deja start_date y end_date en null.

Debes devolver EXACTAMENTE esta estructura:

{
  "EXTRACCION": {
    "contract_json": {
      "frequency": "monthly",
      "start_date": null,
      "end_date": null,
      "currency": null,
      "capex_initial": 0,
      "opex_monthly": 0,
      "discount": {
        "rate_annual": null
      },
      "inflation": {
        "mode": "none",
        "cpi_annual": 0,
        "adjust_every_months": 12
      },
      "rent_fixed": {
        "amount": 0,
        "index_to_inflation": false
      },
      "rent_variable": {
        "enabled": false,
        "share": 0,
        "min_guaranteed": null,
        "max_cap": null,
        "driver_forecast": {
          "base_monthly": 0,
          "g_annual": 0
        }
      }
    },
    "evidence": [
      {
        "field": "nombre_del_campo",
        "source_file": "archivo.pdf",
        "page": 1,
        "chunk": 0,
        "quote": "texto exacto del contrato que respalda el valor"
      }
    ]
  },
  "missing_fields": [],
  "notes": []
}

MAPEO FINANCIERO OBLIGATORIO:
- Si hay renta fija mensual/anual → rent_fixed.amount
- Si está indexada a INPC/CPI → inflation.mode="index"
- Si menciona % sobre ventas/ingresos → rent_variable.enabled=true y rent_variable.share=<decimal>
- Si hay mínimo garantizado → min_guaranteed
- Si hay máximo (cap) → max_cap
- Si existe tasa de descuento explícita → discount.rate_annual
- Si hay anticipo, inversión inicial o CAPEX → capex_initial (como egreso)
- Si hay costos mensuales recurrentes → opex_monthly
- Si el contrato indica periodicidad mensual → frequency="monthly"
- Si indica anual → frequency="annual"

NO realices cálculos.
NO incluyas NPV, IRR ni sensibilidad.
SOLO extrae y estructura datos para que el sistema ejecute herramientas financieras externas.
Recuerda: SOLO JSON válido.
"""


def run_financial_agent(question: str, context: str) -> str:
    """
    Agente Financiero (Extractor):
    - Lee el contexto RAG (fragmentos del contrato)
    - Devuelve SOLO JSON con contract_json + evidence + missing_fields
    """
    user_msg = f"""
CONTRATO (fragmentos relevantes):

{context}

PREGUNTA DEL USUARIO:
{question}

Instrucciones:
1) Extrae datos financieros y condiciones de pago del contrato (renta fija/variable, indexación, mínimos/máximos, fechas, moneda).
2) Devuelve SOLO el JSON con la estructura requerida.
3) Para cada campo importante que completes, agrega evidencia con source_file/page/chunk/quote.
4) Si falta algo para modelar flujos (ej. fechas, tasa de descuento, inflación, base de renta variable), inclúyelo en missing_fields.
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
