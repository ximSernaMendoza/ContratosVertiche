from typing import Dict, Any, List

DEFAULT_RULES = [
    {"factor": "renovacion_automatica", "weight": 20},
    {"factor": "penalidad_mayor_6_meses", "weight": 20},
    {"factor": "incremento_sin_tope", "weight": 12},
    {"factor": "subarrendamiento_prohibido", "weight": 8},
    {"factor": "jurisdiccion_inconveniente", "weight": 10},
    {"factor": "devolver_como_nuevo", "weight": 10},
]

def risk_score(extracted: Dict[str, Any], legal_report: Dict[str, Any]) -> Dict[str, Any]:
    # Heurística simple: si un hallazgo legal high coincide con un factor, suma peso.
    findings = (legal_report.get("findings") or [])
    text = " ".join([(f.get("title","") + " " + f.get("description","")) for f in findings]).lower()

    breakdown: List[Dict[str, Any]] = []
    score = 0

    def hit(keywords): return any(k in text for k in keywords)

    for rule in DEFAULT_RULES:
        f = rule["factor"]
        w = rule["weight"]
        matched = False

        if f == "renovacion_automatica":
            matched = hit(["renovación automática", "renewal automática", "prórroga automática"])
        elif f == "penalidad_mayor_6_meses":
            matched = hit(["> 6 meses", "seis meses", "6 meses", "penalidad desproporcionada"])
        elif f == "incremento_sin_tope":
            matched = hit(["sin tope", "a discreción", "incremento indefinido"])
        elif f == "subarrendamiento_prohibido":
            matched = hit(["prohibido subarrendar", "subarrendamiento prohibido"])
        elif f == "jurisdiccion_inconveniente":
            matched = hit(["jurisdicción", "fuero", "tribunales de"])
        elif f == "devolver_como_nuevo":
            matched = hit(["como nuevo", "condición original", "mejoras a favor del arrendador"])

        s = w if matched else 0
        score += s
        breakdown.append({"factor": f, "peso": w, "score": s, "motivo": "match" if matched else "no_match"})

    score = min(100, score)
    level = "Bajo" if score < 35 else ("Medio" if score < 70 else "Alto")
    return {"total_score_0_100": score, "level": level, "breakdown": breakdown}
