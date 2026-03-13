
from git import Optional
import pandas as pd
import plotly.express as px
import streamlit as st
from typing import Dict, Any, List, Optional
from agents.finance_agent import extract_finance_numbers


class FinanceService:
    def build_chart_data(self, context: str):
        numbers = extract_finance_numbers(context)
        extracted = {
            "lease_type": "retail" if numbers.get("variable_pct") else "comercial",
            "rent": {
                "base_monthly": numbers.get("base_monthly"),
                "variable_pct_over_sales": numbers.get("variable_pct"),
                "breakpoint_sales": numbers.get("breakpoint_sales"),
            },
        }
        finance_inputs = FinanceInputs(
            years=int(numbers.get("lease_years") or 3),
            escalation_rate_annual=(numbers.get("escalation_pct") or 4.0) / 100.0,
        )
        chart_data = project_cashflows(extracted, finance_inputs)
        chart_data["numbers"] = numbers
        return chart_data

    def render_finance_chart(self, chart_data: dict) -> None:
        rows = chart_data.get("table_rows", [])
        numbers = chart_data.get("numbers", {})
        if not rows:
            st.caption("⚠️ No se pudo generar proyección: el contrato no especifica renta mensual.")
            return
        
        currency = numbers.get("currency") or "MXN"
        total = chart_data.get("total_contract_value", 0)
        max_exp = chart_data.get("max_exposure", 0)
        years = chart_data.get("assumptions", {}).get("years", "?")
        escalation = chart_data.get("assumptions", {}).get("escalation_rate_annual", 0)
        
        #KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Valor total contrato", f"${total:,.0f} {currency}")
        k2.metric("Renta máxima mensual", f"${max_exp:,.0f} {currency}")
        k3.metric("Horizonte proyectado", f"{years} año(s)")
        k4.metric("Escalación anual", f"{escalation * 100:.1f}%")

        df_proj = pd.DataFrame(rows)

        # Líneas: renta base, variable y total
        has_variable = df_proj["variable_rent"].sum() > 0
        y_cols = ["base_rent", "total"] if not has_variable else ["base_rent", "variable_rent", "total"]
        color_map = {
            "base_rent":     "#966368",
            "variable_rent": "#d1c18a",
            "total":         "#4f3b06",
        }
        name_map = {
            "base_rent":     "Renta base",
            "variable_rent": "Renta variable",
            "total":         "Total",
        }

        fig = px.line(
            df_proj,
            x="month",
            y=y_cols,
            labels={"month": "Mes", "value": f"Monto ({currency})", "variable": ""},
            title="Proyección de flujos del contrato",
            color_discrete_map=color_map,
        )
        fig.for_each_trace(lambda t: t.update(name=name_map.get(t.name, t.name)))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.6)",
            height=320,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", y=-0.25),
            xaxis=dict(title="Mes", showgrid=False),
            yaxis=dict(title=f"Monto ({currency})", tickformat="$,.0f"),
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver tabla de proyección"):
            st.dataframe(
                df_proj.rename(columns={
                    "month": "Mes",
                    "base_rent": f"Renta base ({currency})",
                    "variable_rent": f"Renta variable ({currency})",
                    "total": f"Total ({currency})",
                }),
                use_container_width=True,
                hide_index=True,
            )

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
