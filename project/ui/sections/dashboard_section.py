from __future__ import annotations

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# GeoJSON (cache)
@st.cache_data
def load_mexico_geojson():
    url = "https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json"
    return requests.get(url, timeout=20).json()

class DashboardSection:

    def render(self) -> None:
        st.markdown("### Dashboard")

        #Datos (demostración, reemplazar con datos reales)
        df = pd.DataFrame({
            "state": ["Aguascalientes","Baja California","Baja California Sur","Campeche","Chiapas","Chihuahua","Ciudad de México","Coahuila","Colima","Durango","Guanajuato","Guerrero","Hidalgo","Jalisco","México","Michoacán","Morelos","Nayarit","Nuevo León","Oaxaca","Puebla","Querétaro","Quintana Roo","San Luis Potosí","Sinaloa","Sonora","Tabasco","Tamaulipas","Tlaxcala","Veracruz","Yucatán","Zacatecas"],
            "count": [4,12,3,2,7,8,18,6,1,3,9,5,4,11,14,6,3,2,13,7,10,5,6,4,8,9,3,5,2,12,4,3]
        })

        #KPI ROW
        total = int(df["count"].sum())
        mx = int(df["count"].max())
        mn = int(df["count"].min())
        avg = float(df["count"].mean())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", f"{total}")
        c2.metric("Máximo", f"{mx}")
        c3.metric("Mínimo", f"{mn}")
        c4.metric("Promedio", f"{avg:.1f}")
        st.write("")

        geo = load_mexico_geojson()

        # Mapa limpio
        fig = px.choropleth(
            df,
            geojson=geo,
            locations="state",
            featureidkey="properties.name",
            color="count",
            hover_name="state",
            hover_data={"count": True, "state": False},
            color_continuous_scale="Sunset",
        )

        # Layout minimalista (sin márgenes, fondo transparente)
        fig.update_geos(
            fitbounds="locations",
            visible=False
        )
        fig.update_layout(
            height=560,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_colorbar=dict(
                title="",
                thickness=10,
                len=0.55,
                outlinewidth=0,
                tickfont=dict(size=11),
            )
        )

        # Dashboard layout: Mapa + ranking
        left, right = st.columns([1.65, 1])

        with left:
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.markdown("#### Top 10 estados")
            top10 = df.sort_values("count", ascending=False).head(10)

            # Bar chart minimalista (misma escala)
            bar = px.bar(
                top10[::-1],  # para que el top esté arriba visualmente
                x="count",
                y="state",
                orientation="h",
                text="count",
            )
            bar.update_traces(
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Conteo: %{x}<extra></extra>"
            )
            bar.update_layout(
                height=560,
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="", showgrid=False, zeroline=False),
                yaxis=dict(title="", showgrid=False),
            )

            st.plotly_chart(bar, use_container_width=True)
