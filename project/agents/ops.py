from openai import OpenAI
from config.settings import SETTINGS

client = SETTINGS.get_openai_client()


OPS_SYSTEM_PROMPT = """
Eres un asistente experto en análisis operativo de contratos de arrendamiento.

Tu tarea es identificar riesgos operativos en contratos comerciales.

Reglas estrictas:
- Extrae únicamente información explícita del contrato.
- No inventes ni infieras datos.
- Si algo no aparece en el contrato indica: "No especificado en contrato".
- Siempre menciona la cláusula cuando sea posible.

Responde en español utilizando texto claro, párrafos y listas.

No devuelvas JSON.
"""


def run_ops_agent(question: str, context: str) -> str:

    MAX_CONTEXT_CHARS = 15000
    context = context[:MAX_CONTEXT_CHARS]

    user_msg = f"""
CONTRATO (fragmentos relevantes):

{context}

PREGUNTA DEL USUARIO:
{question}


PROCESO DE ANÁLISIS (SIGUE ESTOS PASOS):

PASO 1 — Identificación de cláusulas
Revisa cuidadosamente el contrato e identifica todas las cláusulas relevantes.

PASO 2 — Extracción de información
Busca información operativa relacionada con:

- entrega del inmueble
- uso permitido del inmueble
- restricciones de uso
- modificaciones al inmueble
- subarrendamiento o traspaso
- mantenimiento del inmueble
- composturas o reparaciones
- pago de servicios (agua, luz, teléfono)
- depósitos en garantía
- intereses moratorios
- penalidades económicas
- pena convencional
- rescisión por incumplimiento
- obligación de desocupar el inmueble
- permisos o uso de suelo

PASO 3 — Identificación de riesgos operativos

Detecta riesgos como:

- pérdida del depósito
- penalidades económicas
- rescisión del contrato
- obligaciones de reparación
- restricciones de uso del inmueble
- costos ocultos


BUSCA ESPECÍFICAMENTE PALABRAS CLAVE COMO:

- composturas
- arreglos
- reparaciones
- mantenimiento
- subarrendar
- traspasar
- ceder
- penalidad
- pena convencional
- interés moratorio
- rescisión
- desocupar


REGLAS IMPORTANTES:

- Analiza únicamente lo que aparece explícitamente en el contrato.
- No inventes datos.
- Si algo no aparece escribe: "No especificado en contrato".
- Incluye siempre la referencia de la cláusula cuando sea posible.
- Si una cláusula menciona reparaciones o composturas clasifícala como mantenimiento.
- Si menciona subarrendar o traspasar clasifícala como restricción operativa.
- Si menciona intereses por retraso clasifícalo como interés moratorio.


FORMATO DE RESPUESTA:

1 Cláusulas relevantes  
2 Penalidades económicas identificadas  
3 Riesgos operativos detectados  
4 Conclusión operativa del contrato
"""

    resp = client.chat.completions.create(
        model=SETTINGS.CHAT_MODEL,
        messages=[
            {"role": "system", "content": OPS_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0
    )

    return resp.choices[0].message.content or ""
