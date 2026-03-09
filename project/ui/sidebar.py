from __future__ import annotations

import streamlit as st
from core.session_manager import SessionManager


class Sidebar:
    def __init__(self, session: SessionManager) -> None:
        self.session = session

    def render(self) -> None:
        with st.sidebar:
            st.markdown("### Usuario")
            st.write("👤 Vertiche")
            st.markdown("---")
            if st.button("Consulta", key="consulta_link"):
                self.session.section = "consulta"
            if st.button("Subir Documentos", key="subir_link"):
                self.session.section = "subir"
            if st.button("Calendario", key="calendario_link"):
                self.session.section = "calendario"
            if st.button("Dashboard", key="dashboard_link"):
                self.session.section = "dashboard"
