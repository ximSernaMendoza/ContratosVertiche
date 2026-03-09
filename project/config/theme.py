from dataclasses import dataclass
import streamlit as st


@dataclass(frozen=True)
class Theme:
    # Paleta de colores 
    PINK_LIGHT: str = "#d69d96"
    PINK_DARK: str = "#966368"
    BROWN_MAIN: str = "#4f3b06"
    BROWN_SOFT: str = "#6a5320"
    BEIGE: str = "#d1c18a"

    def render_css(self) -> str:
        # CSS
        return f"""
        <style>
        :root {{
            --pink-light: {self.PINK_LIGHT};
            --pink-dark: {self.PINK_DARK};
            --brown-main: {self.BROWN_MAIN};
            --brown-soft: {self.BROWN_SOFT};
            --beige: {self.BEIGE};
            --radius: 16px;
        }}

        /* Fondo general */
        .stApp {{
            background: {self.PINK_LIGHT};
        }}

        /* Barra superior de Streamlit */
        header {{
            background: {self.PINK_LIGHT} !important;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: {self.PINK_DARK};
            border-right: 1px solid rgba(209,193,138,0.25);
        }}

        section[data-testid="stSidebar"] * {{
            color: rgba(255,255,255,1);
        }}

        /* Títulos */
        h1, h2, h3 {{
            color: var(--brown-main);
            letter-spacing: -0.2px;
        }}

        .muted {{
            color: rgba(79,59,6,0.75);
        }}

        /* Top Header */
        .topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 1rem 1.2rem;
            border-radius: var(--radius);
            background: rgba(255,255,255,0.55);
            border: 1px solid rgba(79,59,6,0.14);
            backdrop-filter: blur(8px);
            box-shadow: 0 10px 30px rgba(79,59,6,0.10);
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: .75rem;
        }}

        .logo {{
            width: 40px;
            height: 40px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--pink-dark), var(--pink-light));
            box-shadow: 0 10px 20px rgba(150,99,104,0.30);
            border: 1px solid rgba(79,59,6,0.14);
        }}

        .brand-title {{
            font-weight: 700;
            color: var(--brown-main);
            font-size: 1.05rem;
            line-height: 1.1;
        }}

        .brand-sub {{
            font-size: 0.86rem;
            color: rgba(79,59,6,0.70);
        }}

        .status-pill {{
            display: flex;
            align-items: center;
            gap: .55rem;
            padding: 0.4rem .75rem;
            border-radius: 999px;
            background: rgba(214,157,150,0.22);
            border: 1px solid rgba(150,99,104,0.25);
            color: var(--brown-main);
            font-size: 0.88rem;
            font-weight: 600;
        }}

        .dot {{
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: var(--pink-dark);
            box-shadow: 0 0 0 4px rgba(214,157,150,0.35);
        }}

        /* Cards */
        .card {{
            border-radius: var(--radius);
            background: rgba(255,255,255,0.60);
            border: 1px solid rgba(79,59,6,0.14);
            padding: 1rem;
            box-shadow: 0 12px 28px rgba(79,59,6,0.10);
            backdrop-filter: blur(10px);
        }}

        .kpi-row {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 0rem;
        }}

        .kpi {{
            flex: 1 1 150px;
            border-radius: 14px;
            padding: 0.4rem 1rem;
            background: rgba(255,255,255,0.60);
            border: 1px solid rgba(150,99,104,0.18);
        }}

        .kpi .label {{
            font-size: 1.1rem;
            color: var(--brown-main);
            font-weight: 600;
        }}

        .kpi .value {{
            font-size: 1.1rem;
            font-weight: 800;
            color: rgba(79,59,6,1);
            margin-top: .1rem;
        }}

        /* Chat */
        .msg {{
            display: flex;
            gap: .8rem;
            margin: .55rem 0;
            align-items: flex-end;
        }}

        .avatar {{
            width: 34px;
            height: 34px;
            border-radius: 12px;
            border: 1px solid rgba(79,59,6,0.14);
        }}

        .avatar.user {{
            background: {self.BROWN_SOFT};
        }}

        .avatar.bot {{
            background: linear-gradient(135deg, rgba(150,99,104,0.95), rgba(214,157,150,0.95));
        }}

        .bubble {{
            max-width: 78%;
            padding: .75rem .9rem;
            border-radius: 16px;
            border: 1px solid rgba(79,59,6,0.12);
            box-shadow: 0 10px 20px rgba(79,59,6,0.06);
        }}

        .bubble.user {{
            background: {self.PINK_DARK};
            color: rgba(255,255,255,1);
            border-top-right-radius: 8px;
        }}

        .bubble.bot {{
            background: {self.PINK_LIGHT};
            color: var(--brown-main);
            border-top-left-radius: 8px;
        }}

        .meta {{
            font-size: .75rem;
            color: rgba(255,255,255,1);
            margin-top: .35rem;
        }}

        /* Chips */
        .chips {{
            display: flex;
            gap: .5rem;
            flex-wrap: wrap;
            margin: .75rem 0 1rem 0;
        }}

        .chip-btn button {{
            padding: .45rem .7rem !important;
            border-radius: 999px !important;
            background: rgba(255,255,255,0.55) !important;
            border: 1px solid rgba(79,59,6,0.14) !important;
            color: var(--brown-main) !important;
            font-weight: 700 !important;
            font-size: .85rem !important;
            box-shadow: none !important;
        }}

        .chip-btn button:hover {{
            filter: brightness(0.98);
            transform: translateY(-1px);
        }}

        /* Bottom input bar */
        .bottom-bar {{
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 999;
            padding: .9rem 1rem;
            background: {self.PINK_LIGHT};
            border-top: 1px solid rgba(79,59,6,0.14);
            backdrop-filter: blur(12px);
        }}

        .bottom-inner {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            gap: .6rem;
            align-items: center;
        }}

        .hint {{
            font-size: .85rem;
            color: rgba(79,59,6,0.70);
        }}

        /* Buttons */
        div.stButton > button {{
            border-radius: 12px !important;
            border: 1px solid rgba(79,59,6,0.18) !important;
            background: rgba(255,255,255,0.85) !important;
            color: var(--brown-main) !important;
            font-weight: 700 !important;
            padding: 0.01rem .7rem !important;
            box-shadow: 0 10px 18px rgba(150,99,104,0.25) !important;
        }}

        div.stButton > button:hover {{
            filter: brightness(0.98);
            transform: translateY(-1px);
        }}

        /* Inputs */
        .stTextInput input,
        .stTextArea textarea {{
            color: var(--brown-main) !important;
            border-radius: 1px !important;
            border: 1px solid rgba(255,255,255,0.85) !important;
            background: rgba(250,250,250,0.95) !important;
        }}

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: {self.PINK_DARK} !important;
            opacity: 1 !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab"] {{
            background: rgba(209,193,138,0.20);
            border: 1px solid rgba(79,59,6,0.14);
            border-radius: 12px;
            color: var(--brown-main);
            font-weight: 700;
            padding: .5rem .8rem;
        }}

        .stTabs [aria-selected="true"] {{
            background: rgba(214,157,150,0.22);
            border-color: rgba(150,99,104,0.30);
        }}

        /* Footer */
        .footer {{
            margin-top: .9rem;
            font-size: .82rem;
            color: rgba(79,59,6,0.60);
        }}

        /* Sidebar buttons como links */
        section[data-testid="stSidebar"] .stButton button {{
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            color: {self.BROWN_MAIN} !important;
            font-weight: 500 !important;
            padding: 0 !important;
            text-align: left !important;
        }}

        section[data-testid="stSidebar"] .stButton button:hover {{
            color: {self.PINK_DARK} !important;
            text-decoration: underline !important;
        }}

        section[data-testid="stSidebar"] .stButton {{
            margin-bottom: 0.6rem;
        }}

        /* File uploader */
        [data-testid="stFileUploader"] {{
            border: 2px dashed {self.PINK_DARK} !important;
            border-radius: 16px !important;
            padding: 1.2rem !important;
        }}

        [data-testid="stFileUploader"],
        [data-testid="stFileUploader"] * {{
            color: white !important;
        }}

        [data-testid="stFileUploader"] > div,
        [data-testid="stFileUploader"] section {{
            background-color: rgba(150,99,104,0.35) !important;
        }}

        [data-testid="stFileUploader"] button {{
            background: linear-gradient(135deg, {self.PINK_DARK}, {self.PINK_LIGHT}) !important;
            color: white !important;
            border-radius: 12px !important;
            border: none !important;
        }}

        /* Chat input */
        div[data-testid="stChatInput"] {{
            background-color: rgba(255,255,255,0.9) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(150,99,104,0.25) !important;
        }}

        div[data-testid="stChatInput"] textarea {{
            background-color: rgba(255,255,255,0.95) !important;
            color: {self.BROWN_MAIN} !important;
        }}

        div[data-testid="stChatInput"] textarea::placeholder {{
            color: {self.PINK_DARK} !important;
        }}

        div[data-testid="stChatInput"] button {{
            background: {self.PINK_DARK} !important;
            border-radius: 10px !important;
            border: none !important;
            color: white !important;
        }}

        [data-testid="stChatMessageContainer"] {{
            background-color: {self.PINK_LIGHT} !important;
        }}

        [data-testid="stChatInputContainer"] {{
            background: {self.PINK_LIGHT} !important;
        }}

        [data-testid="stBottomBlockContainer"] {{
            background-color: {self.PINK_LIGHT} !important;
        }}

        /* Selectbox */
        div[data-baseweb="select"] > div {{
            background-color: {self.PINK_DARK} !important;
            color: white !important;
            border: 1px solid rgba(79,59,6,0.25) !important;
        }}

        div[data-baseweb="select"] span {{
            color: {self.BROWN_MAIN} !important;
        }}

        div[data-baseweb="select"] svg {{
            fill: {self.BROWN_MAIN} !important;
        }}

        ul[role="listbox"] {{
            background-color: white !important;
        }}

        ul[role="listbox"] li {{
            color: {self.BROWN_MAIN} !important;
        }}

        div[data-testid="stAlert"] {{
        background-color: #966368!important;
        border-left: 6px solid #966368 !important;
        color: #966368 !important;
        }}

        div[data-testid="stAlert"] p {{
            color: white !important;
        }}

        /* Alert */
        div[data-testid="stAlert"] {{
            background: rgba(214,157,150,0.30) !important;
            border-left: 6px solid {self.PINK_DARK} !important;
            border-radius: 14px !important;
        }}

        div[data-testid="stAlert"] > div,
        div[data-testid="stAlert"] > div > div,
        div[role="alert"] > div,
        div[role="alert"] > div > div {{
            background: transparent !important;
            box-shadow: none !important;
        }}

        div[data-testid="stAlert"] * {{
            color: white !important;
        }}

        div[data-testid="stAlert"] svg {{
            fill: {self.BROWN_MAIN} !important;
        }}

        /* Input deshabilitado */
        input[disabled] {{
            background-color: #986368 !important;
        }}

        /* Labels */
        label {{
            color: {self.BROWN_MAIN} !important;
        }}

        /* Quitar bordes de inputs */
        .stTextInput input {{
            border: none !important;
            box-shadow: none !important;
        }}

        /* Radio buttons */
        div[role="radiogroup"] label {{
            color: {self.PINK_DARK} !important;
        }}

        div[role="radiogroup"] label > div:first-child {{
            border: 2px solid {self.PINK_DARK} !important;
            background: {self.PINK_DARK} !important;
            border-radius: 100% !important;
        }}
        </style>
        """


THEME = Theme()


def apply_theme() -> None:
    st.markdown(THEME.render_css(), unsafe_allow_html=True)