from __future__ import annotations

import os
import re
import pandas as pd
import plotly.express as px
import streamlit as st

from core.auth_service import AuthService
from core.storage_service import StorageService
from core.pdf_service import PdfService
from core.dashboard_extraction_service import DashboardExtractionService


class DashboardSection:
    def __init__(self) -> None:
        self.auth_service = None
        self.storage = None
        self.pdf_service = None
        self.metrics_service = None

        self.estados_mexico = [
            "aguascalientes", "baja california", "baja california sur", "campeche",
            "chiapas", "chihuahua", "ciudad de mexico", "coahuila", "colima",
            "durango", "guanajuato", "guerrero", "hidalgo", "jalisco", "mexico",
            "michoacan", "morelos", "nayarit", "nuevo leon", "oaxaca", "puebla",
            "queretaro", "quintana roo", "san luis potosi", "sinaloa", "sonora",
            "tabasco", "tamaulipas", "tlaxcala", "veracruz", "yucatan", "zacatecas"
        ]

    # ---------------------------------------------------------
    # Inicialización segura de servicios
    # ---------------------------------------------------------
    def _ensure_services(self) -> None:
        if self.auth_service is None:
            self.auth_service = AuthService()

        if self.storage is None:
            self.storage = StorageService(self.auth_service)

        if self.pdf_service is None:
            self.pdf_service = PdfService(self.storage)

        if self.metrics_service is None:
            self.metrics_service =DashboardExtractionService(
                storage=self.storage,
                pdf_service=self.pdf_service
            )

    # ---------------------------------------------------------
    # Filtro para detectar contratos reales y excluir códigos
    # ---------------------------------------------------------
    def _normalize_name(self, value: str) -> str:
        value = value.lower().strip()
        value = value.replace("á", "a").replace("é", "e").replace("í", "i")
        value = value.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        return value

    def _is_state_code_pdf(self, path: str) -> bool:
        """
        Detecta PDFs que en realidad son códigos civiles estatales.
        Ejemplos:
        - Yucatan.pdf
        - Puebla.pdf
        - Colima/Colima.pdf
        """
        base = self._normalize_name(os.path.basename(path))
        no_ext = base.replace(".pdf", "")

        if no_ext in self.estados_mexico:
            return True

        # caso tipo carpeta/estado/nombre_estado.pdf
        full = self._normalize_name(path)
        for estado in self.estados_mexico:
            if full.endswith(f"/{estado}.pdf"):
                return True

        return False

    def _is_federal_code_pdf(self, path: str) -> bool:
        full = self._normalize_name(path)

        patrones = [
            "codigo civil federal",
            "codigo_civil_federal",
            "codigocivilfederal",
            "federal.pdf",
            "federal"
        ]

        return any(p in full for p in patrones)

    def _looks_like_contract_pdf(self, path: str) -> bool:
        """
        Reglas para aceptar contratos:
        - contiene 'contrato'
        - empieza con T...
        - empieza con C01, C02, etc.
        """
        base = os.path.basename(path)
        base_norm = self._normalize_name(base)

        if "contrato" in base_norm:
            return True

        if re.match(r"^t\d+", base_norm):
            return True

        if re.match(r"^c\d+", base_norm):
            return True

        return False

    def _filter_contract_pdfs(self, paths: list[str]) -> list[str]:
        contracts = []

        for path in paths:
            norm = self._normalize_name(path)

            # excluir códigos estatales
            if self._is_state_code_pdf(path):
                continue

            # excluir federal
            if self._is_federal_code_pdf(path):
                continue

            # excluir cualquier PDF que huela a código civil
            if (
                "codigo civil" in norm
                or "codigo_civil" in norm
                or "código civil" in path.lower()
            ):
                continue

            # incluir solo contratos reales
            if self._looks_like_contract_pdf(path):
                contracts.append(path)

        return sorted(set(contracts))

    # ---------------------------------------------------------
    # Construcción del dataset dinámico
    # ---------------------------------------------------------
    @st.cache_data(show_spinner=False)
    def _build_dashboard_dataframe(_self) -> pd.DataFrame:
        _self._ensure_services()

        columnas = [
            "contrato",
            "nombre_archivo",
            "estado",
            "ciudad",
            "renta_mensual",
            "deposito",
            "superficie_m2",
            "fecha_inicio",
            "fecha_fin",
            "meses_vigencia",
            "precio_m2",
            "costo_total",
            "tiene_renta",
            "tiene_deposito",
            "tiene_superficie",
            "tiene_estado",
            "tiene_ciudad",
            "tiene_fecha_inicio",
            "tiene_fecha_fin",
            "tiene_vigencia",
            "campos_detectados",
            "porcentaje_completitud",
            "confianza_dashboard",
            "fuente_renta",
            "fuente_deposito",
            "fuente_superficie",
            "fuente_fechas",
        ]

        try:
            all_pdfs = _self.storage.list_all_pdfs()
        except Exception:
            return pd.DataFrame(columns=columnas)

        contract_pdfs = _self._filter_contract_pdfs(all_pdfs)

        if not contract_pdfs:
            return pd.DataFrame(columns=columnas)

        return _self.metrics_service.build_dashboard_dataframe(contract_pdfs)

    # ---------------------------------------------------------
    # Utilidades visuales
    # ---------------------------------------------------------
    @staticmethod
    def _format_currency(value):
        try:
            return f"${value:,.0f}"
        except Exception:
            return "$0"

    @staticmethod
    def _build_kpi_card(title: str, value: str, subtitle: str = ""):
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.08) 100%);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 18px;
                padding: 18px 22px;
                backdrop-filter: blur(8px);
                box-shadow: 0 8px 24px rgba(0,0,0,0.10);
                min-height: 118px;
            ">
                <div style="
                    font-size: 14px;
                    color: #5E4034;
                    margin-bottom: 10px;
                    font-weight: 700;
                ">
                    {title}
                </div>
                <div style="
                    font-size: 30px;
                    font-weight: 800;
                    color: #FFF7F3;
                    line-height: 1.1;
                ">
                    {value}
                </div>
                <div style="
                    font-size: 12px;
                    color: #7A5A4F;
                    margin-top: 10px;
                ">
                    {subtitle}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def _apply_plot_style(fig, title: str = ""):
        fig.update_layout(
            title=dict(
                text=title,
                x=0.02,
                xanchor="left",
                font=dict(size=18, color="#FFF7F3", family="Arial Black")
            ),
            paper_bgcolor="rgba(15,16,25,0.92)",
            plot_bgcolor="rgba(15,16,25,0.92)",
            font=dict(color="#F8EDE8", size=13),
            margin=dict(l=20, r=20, t=60, b=30),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)"
            ),
        )

        fig.update_xaxes(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            zeroline=False,
            showline=False,
            tickfont=dict(color="#F6E9E2")
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            zeroline=False,
            showline=False,
            tickfont=dict(color="#F6E9E2")
        )

        return fig

    @staticmethod
    def _safe_estado(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "estado" in df.columns:
            df["estado"] = df["estado"].fillna("Desconocido")
            df.loc[df["estado"].astype(str).str.strip() == "", "estado"] = "Desconocido"
        return df

    # ---------------------------------------------------------
    # Render principal
    # ---------------------------------------------------------
    def render(self):
        st.markdown("### Dashboard de contratos")

        try:
            df = self._build_dashboard_dataframe()
        except Exception as e:
            st.error(f"No se pudo construir el dashboard: {e}")
            return

        if df.empty:
            st.warning("No se encontraron contratos válidos con datos suficientes para el dashboard.")
            return

        df = self._safe_estado(df)

        modo = st.radio(
            "Tipo de comparación",
            ["Federal", "Por estado", "Por selección", "Validación"],
            horizontal=True
        )

        if modo == "Federal":
            self.render_federal(df)
        elif modo == "Por estado":
            self.render_estado(df)
        elif modo == "Por selección":
            self.render_seleccion(df)
        elif modo == "Validación":
            self.render_validacion_extraccion(df)
            self.render_diagnostico_debug(df)

    # ---------------------------------------------------------
    # FEDERAL
    # ---------------------------------------------------------
    def render_federal(self, df: pd.DataFrame):
        st.markdown("## Comparación Federal")

        df = df.copy()
        df = df[df["renta_mensual"].notna()].copy()

        if df.empty:
            st.warning("No hay información suficiente para mostrar la comparación federal.")
            return

        df_superficie = df[df["superficie_m2"].notna() & (df["superficie_m2"] > 0)].copy()
        df_precio = df[df["precio_m2"].notna()].copy()

        total_contratos = len(df)
        renta_promedio = df["renta_mensual"].mean()
        superficie_promedio = df_superficie["superficie_m2"].mean() if not df_superficie.empty else None
        precio_m2_promedio = df_precio["precio_m2"].mean() if not df_precio.empty else None

        k1, k2, k3, k4 = st.columns(4)

        with k1:
            self._build_kpi_card(
                "Contratos analizados",
                f"{total_contratos}",
                "Contratos válidos con renta detectada"
            )

        with k2:
            self._build_kpi_card(
                "Renta promedio",
                self._format_currency(renta_promedio),
                "Promedio nacional mensual"
            )

        with k3:
            self._build_kpi_card(
                "Superficie promedio",
                f"{superficie_promedio:,.0f} m²" if superficie_promedio is not None else "N/D",
                "Tamaño promedio"
            )

        with k4:
            self._build_kpi_card(
                "Precio promedio por m²",
                f"${precio_m2_promedio:,.0f}" if precio_m2_promedio is not None else "N/D",
                "Valor promedio del espacio"
            )

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        with c1:
            fig_hist = px.histogram(
                df,
                x="renta_mensual",
                nbins=min(14, max(6, len(df) // 2)),
                opacity=0.95,
            )

            fig_hist.update_traces(
                marker=dict(
                    color="#8ECDF9",
                    line=dict(color="#67B7F7", width=1.2)
                ),
                hovertemplate="<b>Rango de renta</b><br>Contratos: %{y}<br>Renta: %{x}<extra></extra>"
            )

            fig_hist.update_xaxes(
                tickprefix="$",
                separatethousands=True,
                title="Renta mensual"
            )
            fig_hist.update_yaxes(title="Número de contratos")

            fig_hist = self._apply_plot_style(fig_hist, "Distribución de rentas")
            st.plotly_chart(fig_hist, use_container_width=True)

        with c2:
            if df_superficie.empty:
                st.info("No hay datos suficientes para la relación renta vs superficie.")
            else:
                fig_scatter = px.scatter(
                    df_superficie,
                    x="superficie_m2",
                    y="renta_mensual",
                    color="precio_m2",
                    color_continuous_scale=["#F6D6C9", "#EAA9A0", "#B87C9C", "#6DA9FF"],
                    hover_data={
                        "nombre_archivo": True,
                        "estado": True,
                        "superficie_m2": ":.0f",
                        "renta_mensual": ":,.0f",
                        "precio_m2": ":,.0f"
                    }
                )

                fig_scatter.update_traces(
                    marker=dict(
                        size=10,
                        line=dict(width=1, color="rgba(255,255,255,0.35)")
                    )
                )

                fig_scatter.update_xaxes(title="Superficie (m²)")
                fig_scatter.update_yaxes(
                    title="Renta mensual",
                    tickprefix="$",
                    separatethousands=True
                )

                fig_scatter = self._apply_plot_style(fig_scatter, "Relación renta vs superficie")
                st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        col3, col4 = st.columns(2)

        renta_estado = (
            df.groupby("estado", as_index=False)["renta_mensual"]
            .mean()
            .sort_values("renta_mensual", ascending=True)
        )

        with col3:
            fig_renta_estado = px.bar(
                renta_estado,
                x="renta_mensual",
                y="estado",
                orientation="h",
                text="renta_mensual"
            )

            fig_renta_estado.update_traces(
                marker=dict(
                    color="#A7D8FF",
                    line=dict(color="#74BFFF", width=1)
                ),
                texttemplate="$%{text:,.0f}",
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Renta promedio: $%{x:,.0f}<extra></extra>"
            )

            fig_renta_estado.update_xaxes(
                title="Renta promedio",
                tickprefix="$",
                separatethousands=True
            )
            fig_renta_estado.update_yaxes(title="")

            fig_renta_estado = self._apply_plot_style(fig_renta_estado, "Renta promedio por estado")
            fig_renta_estado.update_layout(height=520)
            st.plotly_chart(fig_renta_estado, use_container_width=True)

        precio_estado = (
            df_precio.groupby("estado", as_index=False)["precio_m2"]
            .mean()
            .sort_values("precio_m2", ascending=True)
        )

        with col4:
            if precio_estado.empty:
                st.info("No hay información suficiente para calcular precio promedio por m² por estado.")
            else:
                fig_precio_estado = px.bar(
                    precio_estado,
                    x="precio_m2",
                    y="estado",
                    orientation="h",
                    text="precio_m2"
                )

                fig_precio_estado.update_traces(
                    marker=dict(
                        color="#D4B5FF",
                        line=dict(color="#BF97FF", width=1)
                    ),
                    texttemplate="$%{text:,.0f}",
                    textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Precio promedio por m²: $%{x:,.0f}<extra></extra>"
                )

                fig_precio_estado.update_xaxes(
                    title="Precio promedio por m²",
                    tickprefix="$",
                    separatethousands=True
                )
                fig_precio_estado.update_yaxes(title="")

                fig_precio_estado = self._apply_plot_style(fig_precio_estado, "Precio promedio por m² por estado")
                fig_precio_estado.update_layout(height=520)
                st.plotly_chart(fig_precio_estado, use_container_width=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        st.markdown("### Dispersión de rentas por estado")

        if df["estado"].nunique() <= 1:
            st.info("Se necesitan contratos de más de un estado para mostrar la dispersión por estado.")
        else:
            fig_box = px.box(
                df,
                x="estado",
                y="renta_mensual",
                color="estado",
                points="outliers"
            )
            fig_box.update_layout(showlegend=False)
            fig_box.update_yaxes(
                title="Renta mensual",
                tickprefix="$",
                separatethousands=True
            )
            fig_box.update_xaxes(title="Estado")
            fig_box = self._apply_plot_style(fig_box, "Dispersión de rentas por estado")
            st.plotly_chart(fig_box, use_container_width=True)

        st.markdown("### Resumen por estado")

        resumen = (
            df.groupby("estado", as_index=False)
            .agg(
                contratos=("contrato", "count"),
                renta_promedio=("renta_mensual", "mean"),
                superficie_promedio=("superficie_m2", "mean"),
                precio_m2_promedio=("precio_m2", "mean"),
                confianza_modal=("confianza_dashboard", lambda x: x.mode().iloc[0] if not x.mode().empty else "N/D"),
            )
            .sort_values("renta_promedio", ascending=False)
        )

        resumen["renta_promedio"] = resumen["renta_promedio"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "N/D")
        resumen["superficie_promedio"] = resumen["superficie_promedio"].map(lambda x: f"{x:,.0f} m²" if pd.notna(x) else "N/D")
        resumen["precio_m2_promedio"] = resumen["precio_m2_promedio"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "N/D")

        st.dataframe(
            resumen,
            use_container_width=True,
            hide_index=True
        )

    # ---------------------------------------------------------
    # POR ESTADO
    # ---------------------------------------------------------
    def render_estado(self, df: pd.DataFrame):
        st.markdown("## Comparación por estado")

        estados = sorted([e for e in df["estado"].dropna().unique().tolist() if e])

        if not estados:
            st.warning("No hay estados disponibles para comparar.")
            return

        estado_sel = st.selectbox("Selecciona un estado", estados)

        df_estado = df[df["estado"] == estado_sel].copy()
        df_estado = df_estado[df_estado["renta_mensual"].notna()].copy()

        if df_estado.empty:
            st.info("No hay contratos para el estado seleccionado.")
            return

        df_superficie = df_estado.dropna(subset=["superficie_m2"]).copy()
        df_precio = df_estado.dropna(subset=["precio_m2"]).copy()

        renta_prom_estado = df_estado["renta_mensual"].mean()
        renta_prom_nac = df[df["renta_mensual"].notna()]["renta_mensual"].mean()
        superficie_prom_estado = df_superficie["superficie_m2"].mean() if not df_superficie.empty else None
        superficie_prom_nac = df[df["superficie_m2"].notna()]["superficie_m2"].mean() if df["superficie_m2"].notna().any() else None

        k1, k2, k3, k4 = st.columns(4)

        with k1:
            self._build_kpi_card(
                "Contratos del estado",
                f"{len(df_estado)}",
                f"Contratos detectados en {estado_sel}"
            )

        with k2:
            self._build_kpi_card(
                "Renta promedio estatal",
                self._format_currency(renta_prom_estado),
                "Promedio del estado seleccionado"
            )

        with k3:
            self._build_kpi_card(
                "Promedio nacional",
                self._format_currency(renta_prom_nac),
                "Referencia nacional"
            )

        with k4:
            self._build_kpi_card(
                "Superficie promedio estatal",
                f"{superficie_prom_estado:,.0f} m²" if superficie_prom_estado is not None else "N/D",
                "Promedio de tamaño en el estado"
            )

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            fig_renta = px.bar(
                df_estado.sort_values("renta_mensual", ascending=True),
                x="renta_mensual",
                y="nombre_archivo",
                orientation="h",
                text="renta_mensual"
            )
            fig_renta.update_traces(
                marker=dict(color="#9BD3FF", line=dict(color="#6CBFFF", width=1)),
                texttemplate="$%{text:,.0f}",
                textposition="outside"
            )
            fig_renta.update_xaxes(
                title="Renta mensual",
                tickprefix="$",
                separatethousands=True
            )
            fig_renta.update_yaxes(title="")
            fig_renta = self._apply_plot_style(fig_renta, "Renta mensual en el estado")
            st.plotly_chart(fig_renta, use_container_width=True)

        with col2:
            if df_superficie.empty:
                st.info("No hay información de superficie en este estado.")
            else:
                fig_superficie = px.bar(
                    df_superficie.sort_values("superficie_m2", ascending=True),
                    x="superficie_m2",
                    y="nombre_archivo",
                    orientation="h",
                    text="superficie_m2"
                )
                fig_superficie.update_traces(
                    marker=dict(color="#F3B5C8", line=dict(color="#E89AB5", width=1)),
                    texttemplate="%{text:,.0f} m²",
                    textposition="outside"
                )
                fig_superficie.update_xaxes(title="Superficie (m²)")
                fig_superficie.update_yaxes(title="")
                fig_superficie = self._apply_plot_style(fig_superficie, "Tamaño de inmuebles")
                st.plotly_chart(fig_superficie, use_container_width=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        col3, col4 = st.columns(2)

        with col3:
            if df_precio.empty:
                st.info("No hay información suficiente para calcular precio por metro cuadrado.")
            else:
                fig_precio = px.bar(
                    df_precio.sort_values("precio_m2", ascending=True),
                    x="precio_m2",
                    y="nombre_archivo",
                    orientation="h",
                    text="precio_m2"
                )
                fig_precio.update_traces(
                    marker=dict(color="#CDB4FF", line=dict(color="#B999FF", width=1)),
                    texttemplate="$%{text:,.0f}",
                    textposition="outside"
                )
                fig_precio.update_xaxes(
                    title="Precio por m²",
                    tickprefix="$",
                    separatethousands=True
                )
                fig_precio.update_yaxes(title="")
                fig_precio = self._apply_plot_style(fig_precio, "Precio por metro cuadrado")
                st.plotly_chart(fig_precio, use_container_width=True)

        with col4:
            comparativa = pd.DataFrame({
                "métrica": ["Renta promedio", "Superficie promedio"],
                "estado": [
                    renta_prom_estado,
                    superficie_prom_estado if superficie_prom_estado is not None else 0
                ],
                "nacional": [
                    renta_prom_nac,
                    superficie_prom_nac if superficie_prom_nac is not None else 0
                ]
            })

            fig_compare = px.bar(
                comparativa.melt(id_vars="métrica", var_name="tipo", value_name="valor"),
                x="métrica",
                y="valor",
                color="tipo",
                barmode="group",
                color_discrete_map={
                    "estado": "#8ECDF9",
                    "nacional": "#F3B5C8"
                }
            )
            fig_compare.update_yaxes(title="Valor")
            fig_compare.update_xaxes(title="")
            fig_compare = self._apply_plot_style(fig_compare, "Comparación contra promedio nacional")
            st.plotly_chart(fig_compare, use_container_width=True)

    # ---------------------------------------------------------
    # SELECCIÓN
    # ---------------------------------------------------------
    def render_seleccion(self, df: pd.DataFrame):
        st.markdown("## Comparación por selección")

        contratos = sorted(df["nombre_archivo"].dropna().tolist())

        seleccion = st.multiselect(
            "Selecciona contratos",
            contratos
        )

        if not seleccion:
            st.info("Selecciona contratos para comparar.")
            return

        df_sel = df[df["nombre_archivo"].isin(seleccion)].copy()

        if df_sel.empty:
            st.info("No hay datos para los contratos seleccionados.")
            return

        df_sel = df_sel.sort_values("nombre_archivo")

        col1, col2 = st.columns(2)

        with col1:
            fig_renta = px.bar(
                df_sel,
                x="nombre_archivo",
                y="renta_mensual",
                color="estado",
                text="renta_mensual"
            )
            fig_renta.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig_renta.update_yaxes(title="Renta mensual", tickprefix="$", separatethousands=True)
            fig_renta.update_xaxes(title="Contrato")
            fig_renta = self._apply_plot_style(fig_renta, "Comparación de renta")
            st.plotly_chart(fig_renta, use_container_width=True)

        with col2:
            df_superficie = df_sel.dropna(subset=["superficie_m2"]).copy()
            if df_superficie.empty:
                st.info("No hay información de superficie para los contratos seleccionados.")
            else:
                fig_superficie = px.bar(
                    df_superficie,
                    x="nombre_archivo",
                    y="superficie_m2",
                    color="estado",
                    text="superficie_m2"
                )
                fig_superficie.update_traces(texttemplate="%{text:,.0f} m²", textposition="outside")
                fig_superficie.update_yaxes(title="Superficie (m²)")
                fig_superficie.update_xaxes(title="Contrato")
                fig_superficie = self._apply_plot_style(fig_superficie, "Comparación de superficie")
                st.plotly_chart(fig_superficie, use_container_width=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        col3, col4 = st.columns(2)

        with col3:
            df_precio = df_sel.dropna(subset=["precio_m2"]).copy()
            if df_precio.empty:
                st.info("No hay información suficiente para calcular precio por metro cuadrado.")
            else:
                fig_precio = px.bar(
                    df_precio,
                    x="nombre_archivo",
                    y="precio_m2",
                    color="estado",
                    text="precio_m2"
                )
                fig_precio.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
                fig_precio.update_yaxes(title="Precio por m²", tickprefix="$", separatethousands=True)
                fig_precio.update_xaxes(title="Contrato")
                fig_precio = self._apply_plot_style(fig_precio, "Precio por metro cuadrado")
                st.plotly_chart(fig_precio, use_container_width=True)

        with col4:
            df_costo = df_sel.dropna(subset=["costo_total"]).copy()
            if df_costo.empty:
                st.info("No hay información suficiente para calcular costo total del contrato.")
            else:
                fig_costo = px.bar(
                    df_costo,
                    x="nombre_archivo",
                    y="costo_total",
                    color="estado",
                    text="costo_total"
                )
                fig_costo.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
                fig_costo.update_yaxes(title="Costo total", tickprefix="$", separatethousands=True)
                fig_costo.update_xaxes(title="Contrato")
                fig_costo = self._apply_plot_style(fig_costo, "Costo total del contrato")
                st.plotly_chart(fig_costo, use_container_width=True)

        st.markdown("### Tabla comparativa")
        tabla = df_sel[[
            "nombre_archivo",
            "estado",
            "renta_mensual",
            "superficie_m2",
            "deposito",
            "meses_vigencia",
            "precio_m2",
            "costo_total",
            "confianza_dashboard",
            "fuente_renta",
            "fuente_deposito",
            "fuente_superficie",
            "fuente_fechas",
        ]].copy()
        st.dataframe(tabla, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # VALIDACIÓN
    # ---------------------------------------------------------
    def render_validacion_extraccion(self, df: pd.DataFrame):
        st.markdown("## Validación de extracción")

        total = len(df)
        con_renta = int(df["tiene_renta"].sum()) if "tiene_renta" in df.columns else 0
        con_superficie = int(df["tiene_superficie"].sum()) if "tiene_superficie" in df.columns else 0
        con_fechas = int((df["tiene_fecha_inicio"] & df["tiene_fecha_fin"]).sum()) if "tiene_fecha_inicio" in df.columns and "tiene_fecha_fin" in df.columns else 0
        con_estado = int(df["tiene_estado"].sum()) if "tiene_estado" in df.columns else 0
        alta = int((df["confianza_dashboard"] == "alta").sum()) if "confianza_dashboard" in df.columns else 0
        media = int((df["confianza_dashboard"] == "media").sum()) if "confianza_dashboard" in df.columns else 0
        baja = int((df["confianza_dashboard"] == "baja").sum()) if "confianza_dashboard" in df.columns else 0

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Contratos procesados", total)
        c2.metric("Con renta", con_renta)
        c3.metric("Con superficie", con_superficie)
        c4.metric("Con fechas", con_fechas)
        c5.metric("Con estado", con_estado)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1.2])

        with col1:
            calidad_df = pd.DataFrame({
                "calidad": ["Alta", "Media", "Baja"],
                "cantidad": [alta, media, baja]
            })

            fig_calidad = px.bar(
                calidad_df,
                x="calidad",
                y="cantidad",
                color="calidad",
                color_discrete_map={
                    "Alta": "#7BCFA6",
                    "Media": "#F2C14E",
                    "Baja": "#E76F51",
                },
                title="Calidad de extracción"
            )
            fig_calidad.update_layout(
                xaxis_title="Nivel",
                yaxis_title="Número de contratos",
                showlegend=False
            )
            fig_calidad = self._apply_plot_style(fig_calidad, "Calidad de extracción")
            st.plotly_chart(fig_calidad, use_container_width=True)

        with col2:
            campos = pd.DataFrame({
                "campo": ["Renta", "Depósito", "Superficie", "Estado", "Ciudad", "Fecha inicio", "Fecha fin", "Vigencia"],
                "porcentaje": [
                    round(df["tiene_renta"].mean() * 100, 2) if "tiene_renta" in df.columns else 0,
                    round(df["tiene_deposito"].mean() * 100, 2) if "tiene_deposito" in df.columns else 0,
                    round(df["tiene_superficie"].mean() * 100, 2) if "tiene_superficie" in df.columns else 0,
                    round(df["tiene_estado"].mean() * 100, 2) if "tiene_estado" in df.columns else 0,
                    round(df["tiene_ciudad"].mean() * 100, 2) if "tiene_ciudad" in df.columns else 0,
                    round(df["tiene_fecha_inicio"].mean() * 100, 2) if "tiene_fecha_inicio" in df.columns else 0,
                    round(df["tiene_fecha_fin"].mean() * 100, 2) if "tiene_fecha_fin" in df.columns else 0,
                    round(df["tiene_vigencia"].mean() * 100, 2) if "tiene_vigencia" in df.columns else 0,
                ]
            })

            fig_campos = px.bar(
                campos.sort_values("porcentaje", ascending=True),
                x="porcentaje",
                y="campo",
                orientation="h",
                title="Cobertura por campo"
            )
            fig_campos.update_layout(
                xaxis_title="% de contratos con campo detectado",
                yaxis_title=""
            )
            fig_campos = self._apply_plot_style(fig_campos, "Cobertura por campo")
            st.plotly_chart(fig_campos, use_container_width=True)

        st.markdown("### Tabla de control de calidad")

        columnas_tabla = [
            "nombre_archivo",
            "estado",
            "renta_mensual",
            "superficie_m2",
            "deposito",
            "fecha_inicio",
            "fecha_fin",
            "meses_vigencia",
            "campos_detectados",
            "porcentaje_completitud",
            "confianza_dashboard",
            "fuente_renta",
            "fuente_deposito",
            "fuente_superficie",
            "fuente_fechas",
        ]

        disponibles = [c for c in columnas_tabla if c in df.columns]
        tabla = df[disponibles].copy()

        st.dataframe(
            tabla.sort_values(
                by=["campos_detectados", "porcentaje_completitud"],
                ascending=[False, False]
            ),
            use_container_width=True,
            hide_index=True
        )

    def render_diagnostico_debug(self, df: pd.DataFrame):
        with st.expander("Ver diagnóstico detallado de extracción"):
            columnas_flags = [
                "nombre_archivo",
                "tiene_renta",
                "tiene_deposito",
                "tiene_superficie",
                "tiene_estado",
                "tiene_ciudad",
                "tiene_fecha_inicio",
                "tiene_fecha_fin",
                "tiene_vigencia",
                "confianza_dashboard",
                "texto_extraido_ok",
                "posible_pdf_escaneado",
                "fuente_renta",
                "fuente_deposito",
                "fuente_superficie",
                "fuente_fechas",
            ]

            disponibles = [c for c in columnas_flags if c in df.columns]
            st.dataframe(df[disponibles], use_container_width=True, hide_index=True)