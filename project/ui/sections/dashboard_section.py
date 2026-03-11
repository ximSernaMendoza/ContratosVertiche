from __future__ import annotations

import re
import pandas as pd
import plotly.express as px
import streamlit as st

from core.storage_service import StorageService
from core.pdf_service import PdfService
from config.settings import SETTINGS
from core.auth_service import AuthService


class DashboardSection:

    def __init__(self) -> None:
        self.auth_service = AuthService()
        self.storage = StorageService(self.auth_service)
        self.pdf_service = PdfService(self.storage)

    # ---------------------------------------------------------
    # Utilidades para extraer métricas de los contratos
    # ---------------------------------------------------------

    def extract_renta(self, text: str):
        m = re.search(r"\$([\d,]+\.?\d*)", text)
        if not m:
            return None
        val = m.group(1).replace(",", "")
        try:
            return float(val)
        except:
            return None

    def extract_superficie(self, text: str):
        m = re.search(r"(\d+)\s*m²", text)
        if not m:
            return None
        return float(m.group(1))

    def extract_estado(self, text: str):
        estados = [
            "Aguascalientes","Baja California","Baja California Sur","Campeche","Chiapas","Chihuahua",
            "Ciudad de México","Coahuila","Colima","Durango","Guanajuato","Guerrero","Hidalgo",
            "Jalisco","México","Michoacán","Morelos","Nayarit","Nuevo León","Oaxaca","Puebla",
            "Querétaro","Quintana Roo","San Luis Potosí","Sinaloa","Sonora","Tabasco","Tamaulipas",
            "Tlaxcala","Veracruz","Yucatán","Zacatecas"
        ]

        text_low = text.lower()

        for e in estados:
            if e.lower() in text_low:
                return e

        return "Desconocido"

    # ---------------------------------------------------------
    # Construcción del dataset dinámico
    # ---------------------------------------------------------

    def build_contract_dataframe(self):

        all_pdfs = self.storage.list_all_pdfs()

        rows = []

        for path in all_pdfs:

            text = self.pdf_service.extract_full_pdf_text(path)

            renta = self.extract_renta(text)
            superficie = self.extract_superficie(text)
            estado = self.extract_estado(text)

            if renta is None:
                continue

            precio_m2 = None
            if superficie:
                precio_m2 = renta / superficie

            rows.append({
                "contrato": path,
                "estado": estado,
                "renta": renta,
                "superficie": superficie,
                "precio_m2": precio_m2
            })

        if not rows:
            return pd.DataFrame(columns=[
                "contrato",
                "estado",
                "renta",
                "superficie",
                "precio_m2"
            ])

        return pd.DataFrame(rows)

    # ---------------------------------------------------------
    # Render principal
    # ---------------------------------------------------------

    def render(self):

        st.markdown("### Dashboard de contratos")

        df = self.build_contract_dataframe()

        if df.empty:
            st.warning("No se encontraron datos suficientes en los contratos.")
            return

        modo = st.radio(
            "Tipo de comparación",
            [
                "Federal",
                "Por estado",
                "Por selección"
            ],
            horizontal=True
        )

        if modo == "Federal":
            self.render_federal(df)

        elif modo == "Por estado":
            self.render_estado(df)

        elif modo == "Por selección":
            self.render_seleccion(df)

    # ---------------------------------------------------------
    # FEDERAL
    # ---------------------------------------------------------

    def render_federal(self, df):

        st.markdown("## Comparación Federal")

        c1, c2, c3 = st.columns(3)

        c1.metric("Contratos", len(df))
        c2.metric("Renta promedio", f"${df['renta'].mean():,.0f}")
        c3.metric("Superficie promedio", f"{df['superficie'].mean():.0f} m²")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:

            fig = px.histogram(
                df,
                x="renta",
                nbins=20,
                title="Distribución de rentas"
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:

            fig = px.scatter(
                df,
                x="superficie",
                y="renta",
                title="Relación renta vs superficie"
            )

            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        col3, col4 = st.columns(2)

        renta_estado = (
            df.groupby("estado")["renta"]
            .mean()
            .reset_index()
        )

        fig = px.bar(
            renta_estado,
            x="estado",
            y="renta",
            title="Renta promedio por estado"
        )

        col3.plotly_chart(fig, use_container_width=True)

        precio_estado = (
            df.groupby("estado")["precio_m2"]
            .mean()
            .reset_index()
        )

        fig = px.bar(
            precio_estado,
            x="estado",
            y="precio_m2",
            title="Precio promedio por m² por estado"
        )

        col4.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # POR ESTADO
    # ---------------------------------------------------------

    def render_estado(self, df):

        st.markdown("## Comparación por estado")

        estados = sorted(df["estado"].dropna().unique())

        estado_sel = st.selectbox(
            "Selecciona un estado",
            estados
        )

        df_estado = df[df["estado"] == estado_sel]

        renta_prom_estado = df_estado["renta"].mean()
        renta_prom_nac = df["renta"].mean()

        col1, col2 = st.columns(2)

        col1.metric(
            "Renta promedio del estado",
            f"${renta_prom_estado:,.0f}"
        )

        col2.metric(
            "Promedio nacional",
            f"${renta_prom_nac:,.0f}"
        )

        st.divider()

        col3, col4 = st.columns(2)

        fig = px.bar(
            df_estado,
            x="contrato",
            y="renta",
            title="Renta mensual en el estado"
        )

        col3.plotly_chart(fig, use_container_width=True)

        fig = px.bar(
            df_estado,
            x="contrato",
            y="superficie",
            title="Tamaño de inmuebles"
        )

        col4.plotly_chart(fig, use_container_width=True)

        st.divider()

        fig = px.bar(
            df_estado,
            x="contrato",
            y="precio_m2",
            title="Precio por metro cuadrado"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # SELECCIÓN
    # ---------------------------------------------------------

    def render_seleccion(self, df):

        st.markdown("## Comparación por selección")

        contratos = df["contrato"].tolist()

        seleccion = st.multiselect(
            "Selecciona contratos",
            contratos
        )

        if not seleccion:
            st.info("Selecciona contratos para comparar.")
            return

        df_sel = df[df["contrato"].isin(seleccion)]

        col1, col2 = st.columns(2)

        fig = px.bar(
            df_sel,
            x="contrato",
            y="renta",
            title="Comparación de renta"
        )

        col1.plotly_chart(fig, use_container_width=True)

        fig = px.bar(
            df_sel,
            x="contrato",
            y="superficie",
            title="Comparación de superficie"
        )

        col2.plotly_chart(fig, use_container_width=True)

        st.divider()

        fig = px.bar(
            df_sel,
            x="contrato",
            y="precio_m2",
            title="Precio por metro cuadrado"
        )

        st.plotly_chart(fig, use_container_width=True)