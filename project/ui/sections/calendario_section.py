from __future__ import annotations

import streamlit as st
from streamlit_calendar import calendar


class CalendarioSection:
    def __init__(self, session, calendar_service) -> None:
        self.session = session
        self.calendar_service = calendar_service

    def render(self) -> None:
        st.markdown("### Calendario de contratos")
        st.caption("Eventos: inicio de alerta (3 meses antes) y vencimiento del contrato.")

        events = self.calendar_service.build_calendar_events(st.session_state.contracts)

        options = {
            "initialView": "dayGridMonth",
            "height": 600,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,listWeek"
            },
            "eventDisplay": "block",
        }

        calendar(
        events=events,
        options=options,
        custom_css="""
        .fc {
            background-color: #ffffff;
            color: #4f3b06;
            font-family: 'Segoe UI', sans-serif;
        }

        .fc-daygrid-day-number {
            color: #4f3b06;
        }
        .fc-col-header-cell {
            background-color: #d1c18a;
            color: #4f3b06;
        }
        .fc-day-today {
            background-color: rgba(214,157,150,0.25) !important;
        }
        .fc-button {
            background-color: #966368 !important;
            border: none !important;
        }
        .fc-button:hover {
            background-color: #d69d96 !important;
        }
        """,
        key="full_contracts_calendar"
    )

        # Panel de alertas activas debajo
        st.markdown("#### ⚠️ Alertas activas (ventana 3 meses)")
        alerts = self.calendar_service.compute_alerts(self.session.messages if False else st.session_state.contracts, __import__('datetime').date.today())
        if not alerts:
            st.caption("No hay contratos en ventana de alerta.")
        else:
            for a in alerts:
                days = a["days_left"]

                if days < 30:
                    bg = "rgba(255,80,80,0.15)"
                    border = "#ff4d4d"
                elif days < 60:
                    bg = "rgba(255,165,0,0.18)"
                    border = "#ff9900"
                else:
                    bg = "rgba(214,157,150,0.25)"
                    border = "#966368"

                st.markdown(
                    f"""
                    <div style="
                        background: {bg};
                        border-left: 6px solid {border};
                        padding: 0.8rem;
                        border-radius: 10px;
                        color: #white !important;
                        font-weight: 600;
                        margin-bottom: 0.5rem;
                    ">
                    ⚠️ <b>{a['title']}</b> · vence <b>{a['expiry']}</b> · faltan <b>{a['days_left']}</b> días
                    </div>
                    """,
                    unsafe_allow_html=True
                )
