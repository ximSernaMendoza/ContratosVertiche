from __future__ import annotations

import streamlit as st
from core.storage_service import StorageService


class UIComponents:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    @staticmethod
    def safe_html_text(text: str) -> str:
        return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    def render_sources(self, sources: list) -> None:
        if not sources:
            return

        files = {}
        for s in sources:
            fname = s["file"]
            if fname not in files:
                files[fname] = []
            if s["page"] not in files[fname]:
                files[fname].append(s["page"])

        with st.expander(f"📄 Fuentes consultadas ({len(files)} archivo(s))"):
            for fname, pages in files.items():
                numeric_pages = sorted([p for p in pages if isinstance(p, int)])
                special_pages = [p for p in pages if not isinstance(p, int)]

                parts = [f"p.{p}" for p in numeric_pages] + [str(p) for p in special_pages]
                pages_str = ", ".join(parts)

                col_name, col_btn = st.columns([3, 1])
                with col_name:
                    st.markdown(f"**{fname}**  \n`{pages_str}`")
                with col_btn:
                    url = self.storage.create_signed_url(fname)
                    if url:
                        st.link_button("Ver PDF", url)
                    else:
                        st.caption("Sin enlace")

    def render_chat_messages(self, messages: list[dict], finance_service) -> None:
        for message in messages:
            role = message.get("role", "")
            text = self.safe_html_text(message.get("text", ""))
            if role == "user":
                st.markdown(f'<div class="msg" style="justify-content:flex-end;"><div class="bubble user">{text}</div><div class="avatar user"></div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="msg" style="justify-content:flex-start;"><div class="avatar bot"></div><div class="bubble bot">{text}</div></div>', unsafe_allow_html=True)
                if message.get("chart_data"):
                    finance_service.render_finance_chart(message["chart_data"])
                if message.get("sources"):
                    self.render_sources(message["sources"])
