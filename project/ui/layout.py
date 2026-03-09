from __future__ import annotations

from datetime import datetime
import streamlit as st


class Layout:
    @staticmethod
    def render_topbar(active_alerts: int) -> None:
        icon = "🟢" if active_alerts == 0 else "🔴"
        left, right = st.columns([1.7, 0.9], vertical_alignment="top")
        with left:
            st.markdown(
                """
                <div class="topbar">
            <div class="brand">
                <div class="logo"></div>
                <div>
                <div class="brand-title">Asistente Virtual Vertiche</div>
                <div class="brand-sub">Análisis de Contratos</div>
                </div>
            </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            st.markdown(
                f"""
                <div class="kpi-row">
                <div class="kpi">
                <div class="label">Alertas activas</div>
                <div class="value">{active_alerts} {icon}</div>
                </div>
                <div class="kpi">
                <div class="label">Fecha</div>
                <div class="value">{datetime.now().strftime("%d/%m/%y")}</div>
                </div>
            </div>
            </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

    @staticmethod
    def render_footer() -> None:
        st.markdown('<div class="footer">© Vertiche · Tecnológico de Monterrey CEM</div>', unsafe_allow_html=True)
        st.markdown('<div class="footer">Ximena Serna Mendoza · Tamara Alejandra Ortiz Villareal · Nathan Isaac García Larios · Mauricio Aguilar Pacheco</div>', unsafe_allow_html=True)
