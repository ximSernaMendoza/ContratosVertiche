from __future__ import annotations

from datetime import date
import streamlit as st
from config.settings import SETTINGS
from config.theme import apply_theme
from core.auth_service import AuthService
from core.session_manager import SessionManager
from core.storage_service import StorageService
from core.pdf_service import PdfService
from core.rag_service import RagService
from core.chat_service import ChatService
from core.legal_service import LegalService
from core.finance_service import FinanceService
from core.calendar_service import CalendarService
from ui.layout import Layout
from ui.sidebar import Sidebar
from ui.components import UIComponents
from ui.sections.consulta_section import ConsultaSection
from ui.sections.subir_section import SubirSection
from ui.sections.calendario_section import CalendarioSection
from ui.sections.dashboard_section import DashboardSection


class VerticheApp:
    def __init__(self) -> None:
        st.set_page_config(
            page_title=SETTINGS.page_title,
            page_icon=SETTINGS.page_icon,
            layout=SETTINGS.layout,
            initial_sidebar_state=SETTINGS.initial_sidebar_state,
        )
        self.auth_service = AuthService()
        self.auth_service.init_session_state()

        self.session = SessionManager()
        self.storage = StorageService(self.auth_service)
        self.pdf_service = PdfService(self.storage)
        self.rag_service = RagService(self.pdf_service)
        self.chat_service = ChatService()
        self.legal_service = LegalService(self.pdf_service, self.rag_service)
        self.finance_service = FinanceService()
        self.calendar_service = CalendarService()
        self.components = UIComponents(self.storage)
        self.sidebar = Sidebar(self.session, self.auth_service)
        self.layout = Layout()

        self.consulta_section = ConsultaSection(
            self.session, self.storage, self.pdf_service, self.rag_service,
            self.chat_service, self.legal_service, self.finance_service, self.components,
        )
        self.subir_section = SubirSection(self.storage)
        self.calendario_section = CalendarioSection(self.session, self.calendar_service)
        self.dashboard_section = DashboardSection()

    def run(self) -> None:
        self.session.initialize()
        apply_theme()

        if not self.auth_service.is_configured():
            st.error("Supabase no está configurado. Revisa SUPABASE_URL y SUPABASE_KEY.")
            st.stop()

        if not self.auth_service.require_auth():
            self.auth_service.render_login_screen()
            st.stop()
            
        alerts = self.calendar_service.compute_alerts(st.session_state.contracts, date.today())
        if alerts:
            st.toast(f"⏳ '{alerts[0]['title']}' vence en {alerts[0]['days_left']} días (vence {alerts[0]['expiry']})")
        self.sidebar.render()
        self.layout.render_topbar(len(alerts))
        section = self.session.section
        if section == "consulta":
            self.consulta_section.render()
        elif section == "subir":
            self.subir_section.render()
        elif section == "calendario":
            self.calendario_section.render()
        elif section == "dashboard":
            self.dashboard_section.render()
        self.layout.render_footer()


if __name__ == "__main__":
    VerticheApp().run()
