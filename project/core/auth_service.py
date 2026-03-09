from __future__ import annotations

import base64
import json
import time
from typing import Optional

import streamlit as st
from supabase import create_client, Client

from config.settings import SETTINGS


class AuthService:
    def __init__(self) -> None:
        self.supabase: Optional[Client] = None

        if SETTINGS.SUPABASE_URL and SETTINGS.SUPABASE_KEY:
            self.supabase = create_client(
                SETTINGS.SUPABASE_URL,
                SETTINGS.SUPABASE_KEY
            )

    def is_configured(self) -> bool:
        return self.supabase is not None

    def init_session_state(self) -> None:
        defaults = {
            "user": None,
            "access_token": None,
            "refresh_token": None,
            "is_admin": False,
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def login(self, email: str, password: str) -> tuple[bool, str]:
        if not self.supabase:
            return False, "Supabase no está configurado."

        if not email or not password:
            return False, "Por favor ingresa correo y contraseña."

        try:
            res = self.supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state["user"] = res.user
            st.session_state["access_token"] = res.session.access_token
            st.session_state["refresh_token"] = res.session.refresh_token
            self.restore_user_session()
            self.load_user_role()
            return True, "Inicio de sesión correcto."
        except Exception:
            return False, "Correo o contraseña incorrectos."

    def logout(self) -> None:
        if self.supabase:
            try:
                self.supabase.auth.sign_out()
            except Exception:
                pass

        st.session_state["user"] = None
        st.session_state["access_token"] = None
        st.session_state["refresh_token"] = None
        st.session_state["is_admin"] = False

    def session_expired(self) -> bool:
        token = st.session_state.get("access_token")
        if not token:
            return True

        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            decoded = base64.b64decode(payload)
            exp = json.loads(decoded).get("exp", 0)
            return time.time() > exp
        except Exception:
            return False

    def restore_user_session(self) -> None:
        if not self.supabase:
            return

        access_token = st.session_state.get("access_token")
        refresh_token = st.session_state.get("refresh_token") or ""

        if access_token:
            try:
                self.supabase.auth.set_session(access_token, refresh_token)
            except Exception:
                pass

    def load_user_role(self) -> None:
        if not self.supabase:
            st.session_state["is_admin"] = False
            return

        user = st.session_state.get("user")
        if not user:
            st.session_state["is_admin"] = False
            return

        try:
            user_id = str(user.id)
            resp = (
                self.supabase
                .table("user_roles")
                .select("role")
                .eq("user_id", user_id)
                .execute()
            )
            roles = [r["role"] for r in (resp.data or [])]
            st.session_state["is_admin"] = "admin" in roles
        except Exception:
            st.session_state["is_admin"] = False

    def require_auth(self) -> bool:
        user = st.session_state.get("user")

        if user is None or self.session_expired():
            if user is not None and self.session_expired():
                st.warning("Tu sesión expiró. Por favor inicia sesión de nuevo.")
                self.logout()
            return False

        self.restore_user_session()
        return True

    def render_login_screen(self) -> None:
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("## Bienvenido a Vertiche")
            st.markdown("Ingresa tus credenciales para continuar.")

            email = st.text_input(
                "Correo electrónico",
                placeholder="usuario@correo.com",
                key="login_email"
            )
            password = st.text_input(
                "Contraseña",
                type="password",
                key="login_password"
            )

            if st.button("Iniciar sesión", use_container_width=True):
                ok, msg = self.login(email, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)