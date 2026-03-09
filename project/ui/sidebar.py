from __future__ import annotations

import streamlit as st
from core.session_manager import SessionManager
from core.auth_service import AuthService


class Sidebar:
    def __init__(self, session: SessionManager, auth_service: AuthService) -> None:
        self.session = session
        self.auth_service = auth_service

    def render(self) -> None:
        with st.sidebar:
            st.markdown("### Usuario")
            st.write(f"👤 {self.auth_service.current_user_email()}")
            if st.session_state.get("is_admin"):
                st.caption("Rol: admin")
            else:
                st.caption("Rol: usuario")

            if st.button("Cerrar sesión", use_container_width=True):
                self.auth_service.logout()
                st.rerun()
            
            st.markdown("---")
            
            if st.button("Consulta", key="consulta_link"):
                self.session.section = "consulta"
            if st.button("Subir Documentos", key="subir_link"):
                self.session.section = "subir"
            if st.button("Calendario", key="calendario_link"):
                self.session.section = "calendario"
            if st.button("Dashboard", key="dashboard_link"):
                self.session.section = "dashboard"
