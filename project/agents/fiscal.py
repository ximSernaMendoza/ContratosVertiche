from openai import OpenAI

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")


FISCAL_SYSTEM_PROMPT = """
Eres un contador fiscalista experto en contratos de arrendamiento comercial en México.

Analiza SOLO con base en el contexto proporcionado.

Evalúa:

- Tratamiento de IVA
- Retenciones (IVA / ISR)
- Facturación / CFDI
- Deducibilidad fiscal
- Riesgos fiscales

Clasifica los riesgos como:
Alto / Medio / Bajo

No asumas obligaciones fiscales que no estén explícitamente mencionadas en el contrato.
Si algo no aparece en el texto, indica que no está especificado.

Cuando identifiques omisiones fiscales,
solo puedes mencionar elementos relacionados con:

• emisión de CFDI o facturación
• tipo de retenciones fiscales aplicables
• mención explícita del tratamiento del IVA

No generes omisiones fiscales por tu cuenta.
Las omisiones fiscales se detectan automáticamente por el sistema.

No inventes omisiones fiscales. Solo analiza el contrato.

Responde únicamente con información que esté explícitamente mencionada en el contrato.
No hagas suposiciones ni inferencias fiscales que no aparezcan en el texto.
Si la información no está presente, indica claramente que no está especificada en el contrato.

Si el contrato menciona IVA explícitamente, identifícalo y analízalo.
No afirmes que no se menciona IVA si aparece en el texto.


"""


# ----------------------------
# Detectar traslado de IVA
# ----------------------------

def iva_trasladado(context: str):

    ctx = context.lower()

    patrones = [
    "más iva",
    "mas iva",
    "iva respectivo",
    "iva correspondiente",
    "iva adicional",
    "más el impuesto al valor agregado",
    "mas el impuesto al valor agregado",
    "más el iva",
    "mas el iva"
]

    return any(p in ctx for p in patrones)



# ----------------------------
# Detectar si se menciona IVA
# ----------------------------

def menciona_iva(context: str):

    ctx = context.lower()

    patrones = [
        "iva",
        "impuesto al valor agregado"
    ]

    return any(p in ctx for p in patrones)


# ----------------------------
# Detectar si la pregunta es sobre IVA
# ----------------------------

def pregunta_sobre_iva(question: str):

    q = question.lower()

    palabras = [
        "iva",
        "impuesto al valor agregado"
    ]

    return any(p in q for p in palabras)


# ----------------------------
# Detectar omisiones fiscales
# ----------------------------

def detect_missing_fiscal_clauses(context: str):

    ctx = context.lower()
    missing = []

    # CFDI / facturación
    if "cfdi" not in ctx and "factura" not in ctx:
        missing.append("No se menciona CFDI / facturación")

    # Retenciones no mencionadas
    if "retencion" not in ctx and "retenciones" not in ctx:
        missing.append("No se mencionan retenciones")

    # IVA no mencionado
    if "iva" not in ctx and "impuesto al valor agregado" not in ctx:
        missing.append("No se menciona el tratamiento del IVA")

    return missing


# ----------------------------
# Filtrar contexto fiscal
# ----------------------------

def filter_fiscal_context(context: str):

    keywords = [
        "iva",
        "impuesto",
        "retencion",
        "retenciones",
        "cfdi",
        "factura",
        "fiscal"
    ]

    lines = context.split("\n")

    filtered = [
        line for line in lines
        if any(k in line.lower() for k in keywords)
    ]

    # si hay muy poco contexto fiscal devolvemos todo
    if len(filtered) < 5:
        return context

    return "\n".join(filtered)


# ----------------------------
# Agente fiscal
# ----------------------------

def run_fiscal_agent(question: str, context: str) -> str:

    context = filter_fiscal_context(context)

    MAX_CONTEXT_CHARS = 5000

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS]

    missing = detect_missing_fiscal_clauses(context)

    es_pregunta_iva = pregunta_sobre_iva(question)

    # -----------------------------------
    # Caso claro: IVA trasladado
    # -----------------------------------

    if iva_trasladado(context) and es_pregunta_iva:

        answer = """
ANÁLISIS FISCAL

Tratamiento de IVA
El contrato establece que la renta se paga más el Impuesto al Valor Agregado (IVA).

Interpretación fiscal
Esto significa que el IVA se traslada adicionalmente al arrendatario.

Conclusión
El IVA NO está incluido en la renta.
Se cobra adicionalmente sobre la renta base.

Riesgos fiscales
No se identifican riesgos fiscales en el tratamiento del IVA.
"""

    # -----------------------------------
    # Caso: se menciona IVA pero no es claro
    # -----------------------------------

    elif menciona_iva(context) and es_pregunta_iva:

        answer = """
ANÁLISIS FISCAL

El contrato menciona el Impuesto al Valor Agregado (IVA).

Sin embargo, el texto no permite determinar con claridad
si el IVA está incluido en la renta o si se cobra adicionalmente.

Se requiere revisar la cláusula correspondiente
para confirmar el tratamiento fiscal del IVA.
"""

    # -----------------------------------
    # Caso general → usar LLM
    # -----------------------------------

    else:

        user_msg = f"""
CONTRATO (fragmentos fiscales relevantes):

{context}

PREGUNTA DEL USUARIO:
{question}
"""

        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": FISCAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
        )

        answer = resp.choices[0].message.content or ""

    # -----------------------------------
    # Bloque de omisiones
    # -----------------------------------

    omissions = ""

    if missing:

        omissions = "\n\nOMISIONES DETECTADAS AUTOMÁTICAMENTE:\n"

        for m in missing:
            omissions += f"- {m}\n"

    return answer + omissions