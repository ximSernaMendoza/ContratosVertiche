from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import streamlit as st
from config.settings import SETTINGS


@dataclass
class SessionManager:
    def initialize(self) -> None:
        defaults = {
            "section": "consulta",
            "messages": [],
            "question_draft": "",
            "auto_submit_question": None,
            "clear_question_input": False,
            "contracts": self._demo_contracts(),
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _demo_contracts(self) -> list[dict]:
        rows = []
        for item in SETTINGS.demo_contracts:
            rows.append({**item, "expiry": date.fromisoformat(item["expiry"])})
        return rows

    @property
    def section(self) -> str:
        return st.session_state.section

    @section.setter
    def section(self, value: str) -> None:
        st.session_state.section = value

    @property
    def messages(self) -> list[dict]:
        return st.session_state.messages

    def append_user_message(self, text: str) -> None:
        st.session_state.messages.append({"role": "user", "text": text})

    def append_bot_message(self, text: str, sources=None, chart_data=None) -> None:
        payload = {"role": "bot", "text": text}
        if sources:
            payload["sources"] = sources
        if chart_data is not None:
            payload["chart_data"] = chart_data
        st.session_state.messages.append(payload)

    def normalize_messages(self) -> None:
        normalized = []
        for msg in st.session_state.messages:
            if isinstance(msg, dict):
                normalized.append({
                    "role": msg.get("role", "bot"),
                    "text": msg.get("text", ""),
                    "sources": msg.get("sources"),
                    "chart_data": msg.get("chart_data"),
                })
            else:
                normalized.append({"role": "bot", "text": str(msg)})
        st.session_state.messages = normalized

    def set_auto_submit(self, question: str | None) -> None:
        st.session_state.auto_submit_question = question

    def get_auto_submit(self) -> str | None:
        return st.session_state.auto_submit_question

    def clear_question_input_on_next_render(self) -> None:
        st.session_state.clear_question_input = True

    def consume_clear_question_flag(self) -> bool:
        flag = bool(st.session_state.clear_question_input)
        st.session_state.clear_question_input = False
        return flag
