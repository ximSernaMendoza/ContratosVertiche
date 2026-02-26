# agents/router.py
from agents.legal import run_legal_agent
from agents.fiscal import run_fiscal_agent
# cuando tengan sus agente, los importan amigos :)
# from agents.tax_mx import run_tax_agent
from agents.finance_agent import run_financial_agent
# from agents.ops import run_ops_agent

#Este es en lo que ponen sus demás agentes jiji
def _stub_agent(nombre: str):
    def _runner(question: str, context: str) -> str:
        return f"El agente {nombre} todavía no está implementado. Solo está activo el agente Legal."
    return _runner


# Stubs temporales para que no truene mientras no están listos
run_ops_agent = _stub_agent("Operaciones")
run_tax_agent = run_fiscal_agent

AGENTS = {
    "legal": {
        "label": "Agente Legal",
        "description": (
            "Analiza el contrato desde la perspectiva legal:\n"
            "- Cláusulas abusivas\n"
            "- Terminación unilateral\n"
            "- Penalidades desproporcionadas\n"
            "- Responsabilidad por daños estructurales\n"
            "- Obligaciones de mantenimiento\n"
            "- Cesión o subarrendamiento\n"
            "- Renovación automática\n"
            "- Jurisdicción inconveniente\n"
            "- Contradicciones entre anexos"
        ),
        "runner": run_legal_agent,
    },
    "fiscal": {
        "label": "Agente Fiscal",
        "description": (
            "Analiza el contrato desde la perspectiva fiscal en México:\n"
            "- IVA trasladado o no\n"
            "- Retenciones\n"
            "- Facturación (CFDI)\n"
            "- Deducibilidad\n"
            "- Tratamiento contable (NIIF 16 / IFRS 16, si aplica)"
        ),
        "runner": run_tax_agent,
    },
    "finanzas": {
        "label": "Agente Finanzas",
        "description": (
            "Analiza el contrato desde la perspectiva financiera:\n"
            "- Renta fija y variable\n"
            "- Incrementos (escalation)\n"
            "- Plazo del contrato\n"
            "- Penalidades económicas\n"
            "- Impacto en flujo de caja y riesgo financiero"
        ),
        "runner": run_financial_agent,
    },
    "operaciones": {
        "label": "Agente Operaciones",
        "description": (
            "Analiza el contrato desde la perspectiva operativa:\n"
            "- Obligaciones de mantenimiento\n"
            "- Horarios de operación\n"
            "- Accesos y servicios\n"
            "- Multas operativas\n"
            "- Riesgos para la operación diaria del local/oficina"
        ),
        "runner": run_ops_agent,
    },
}


def list_agents():
    """
    Devuelve el diccionario de agentes para que la UI sepa qué mostrar.
    """
    return AGENTS


def run_orchestrator(question: str, context: str, agent_key=None) -> dict:
    """
    Si agent_key es None -> ejecuta todos los agentes.
    Si agent_key es una key válida -> ejecuta solo ese agente.
    """
    results = {}

    if agent_key is not None:
        meta = AGENTS.get(agent_key)
        if not meta:
            return {"error": f"Agente desconocido: {agent_key}"}
        results[agent_key] = meta["runner"](question, context)
        return results

    # Si no se especifica agente, corre todos
    for key, meta in AGENTS.items():
        results[key] = meta["runner"](question, context)

    return results