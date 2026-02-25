from openai import OpenAI

LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

client = OpenAI(base_url=LMSTUDIO_BASE, api_key="lm-studio")

FISCAL_SYSTEM_PROMPT = """
Eres un contador fiscalista experto en contratos de arrendamiento comercial en México.

Analizas SOLO con base en el contexto proporcionado.
No inventes información.

Evalúa:
- Tratamiento de IVA
- Traslado de IVA
- Retenciones (IVA / ISR)
- Facturación / CFDI
- Deducibilidad fiscal
- Riesgos fiscales ante SAT
- Omisiones contractuales relevantes en materia fiscal

Clasifica los riesgos como:
Alto / Medio / Bajo


Interpretación fiscal mexicana obligatoria (estricta):

- "IVA incluido" → El IVA YA está dentro del monto de la renta.
- "Más IVA", "IVA respectivo", "IVA correspondiente" → El IVA se TRASLADA ADICIONALMENTE.

Regla obligatoria:
Si el contrato contiene expresiones como:
"más IVA", "IVA respectivo", "IVA correspondiente"

DEBES concluir:
→ El IVA NO está incluido en la renta.
→ El IVA se cobra adicionalmente.

Está PROHIBIDO interpretar "IVA respectivo" como IVA incluido.

La deducibilidad fiscal SÍ es relevante en contratos de arrendamiento,
particularmente para el arrendatario.

No clasifiques como riesgo el hecho de que una parte
pueda ser persona física o moral.

Solo considera riesgo si genera ambigüedad u obligación fiscal incierta.

No clasifiques como riesgo fiscal la posibilidad genérica
de incumplimiento de pago.Si el contrato establece "más IVA", NO lo clasifiques como omisión.

El traslado de IVA ("más IVA") NO constituye un riesgo fiscal. 
Solo clasifícalo como riesgo si existe ambigüedad o contradicción. 

No clasifiques como riesgo la posibilidad genérica de error de cálculo del IVA.
Evalúa únicamente riesgos derivados del texto contractual.

NO repitas las instrucciones en la respuesta final.
"""

# Detectar omisiones fiscales
def detect_missing_fiscal_clauses(context: str):
    ctx = context.lower()
    missing = []

    if "iva" not in ctx:
        missing.append("No se menciona IVA")

    if "cfdi" not in ctx and "factura" not in ctx:
        missing.append("No se menciona CFDI / facturación")

    if "retencion" not in ctx:
        missing.append("No se mencionan retenciones")

    return missing

# Resumen de riesgo fiscal
def fiscal_risk_summary(text: str):
    t = text.lower()

    score = 0
    if "riesgo alto" in t:
        score += 3
    if "riesgo medio" in t:
        score += 2
    if "riesgo bajo" in t:
        score += 1

    if score <= 2:
        return "Riesgo fiscal general: Bajo"
    elif score <= 5:
        return "Riesgo fiscal general: Medio"
    else:
        return "Riesgo fiscal general: Alto"
    
# Función principal del agente
def run_fiscal_agent(question: str, context: str) -> str:

    missing_clauses = detect_missing_fiscal_clauses(context)

    user_msg = f"""
CONTRATO (fragmentos relevantes):

{context}

PREGUNTA DEL USUARIO:
{question}

Instrucciones:
1. Identifica implicaciones fiscales relevantes
2. Detecta riesgos fiscales potenciales
3. Clasifica riesgos como Alto / Medio / Bajo
4. Explica impacto fiscal
5. Cita texto exacto del contrato cuando sea posible
6. Señala omisiones fiscales relevantes
"""

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": FISCAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )

    llm_answer = resp.choices[0].message.content or ""

    summary = fiscal_risk_summary(llm_answer)

    omissions_block = ""
    if missing_clauses:
        omissions_block = "\n\n OMISIONES DETECTADAS AUTOMÁTICAMENTE:\n"
        for m in missing_clauses:
            omissions_block += f"- {m}\n"

    final_answer = (
        f"{summary}\n\n"
        f"{llm_answer}"
        f"{omissions_block}"
    )

    return final_answer

# Filtrar contexto fiscal
def filter_fiscal_context(context: str):
    fiscal_keywords = ["iva", "impuesto", "retencion", "cfdi", "factura"]
    lines = context.split("\n")

    filtered = [
        line for line in lines
        if any(k in line.lower() for k in fiscal_keywords)
    ]

    return "\n".join(filtered)