from typing import Dict, Any, List

def build_calendar(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    term = extracted.get("term", {}) or {}
    start = term.get("start_date_iso")
    end = term.get("end_date_iso")
    notice = term.get("notice_days_before_end", 90) or 90

    items = []
    if start:
        items.append({
            "name": "Inicio de contrato",
            "date_iso": start,
            "reminder_days_before": [7, 1],
            "notes": "Verificar condiciones de entrega/acta."
        })
    if end:
        items.append({
            "name": "Fin de contrato",
            "date_iso": end,
            "reminder_days_before": [notice, 60, 30],
            "notes": "Evitar renovación accidental; preparar negociación o salida."
        })
    return items
