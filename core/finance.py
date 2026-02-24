from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd

@dataclass
class FinanceInputs:
    years: int = 5
    monthly_sales: Optional[float] = None  # retail scenario
    escalation_rate_annual: float = 0.04   # fallback si no hay INPC

def project_cashflows(extracted: Dict[str, Any], fin: FinanceInputs) -> Dict[str, Any]:
    rent = extracted.get("rent", {}) or {}
    base_monthly = float(rent.get("base_monthly", 0) or 0)
    is_retail = extracted.get("lease_type") == "retail"

    # Retail: variable rent
    var_pct = float(rent.get("variable_pct_over_sales", 0) or 0) / 100.0
    breakpoint = float(rent.get("breakpoint_sales", 0) or 0)

    rows: List[Dict[str, Any]] = []
    total = 0.0
    max_exposure = 0.0

    months = fin.years * 12
    current_base = base_monthly

    for m in range(1, months + 1):
        # Escalación anual simple (puedes reemplazar por INPC real si lo integras)
        if m % 12 == 1 and m > 1:
            current_base *= (1 + fin.escalation_rate_annual)

        variable = 0.0
        if is_retail and fin.monthly_sales is not None and var_pct > 0:
            sales = fin.monthly_sales
            if breakpoint > 0:
                variable = max(0.0, (sales - breakpoint) * var_pct)
            else:
                variable = sales * var_pct

        month_total = current_base + variable
        total += month_total
        max_exposure = max(max_exposure, month_total)

        rows.append({
            "month": m,
            "base_rent": round(current_base, 2),
            "variable_rent": round(variable, 2),
            "total": round(month_total, 2)
        })

    df = pd.DataFrame(rows)

    return {
        "assumptions": {
            "years": fin.years,
            "monthly_sales": fin.monthly_sales,
            "escalation_rate_annual": fin.escalation_rate_annual
        },
        "table_rows": df.head(24).to_dict(orient="records"),  # muestra 24 meses; full lo guardas si quieres
        "total_contract_value": float(round(total, 2)),
        "max_exposure": float(round(max_exposure, 2)),
        "break_even": None
    }
