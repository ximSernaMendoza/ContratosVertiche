from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class AppConfig:
    # Configuración general de la aplicación
    page_title: str = "Asistente Virtual 2.0 | Vertiche"
    page_icon: str = "💬"
    layout: str = "wide"
    initial_sidebar_state: str = "expanded"

    # Configuración de Supabase
    SUPABASE_URL: str = "https://lvthchgaspfbuybtrkoe.supabase.co"
    SUPABASE_KEY: str = "sb_secret_Uft6Yv-x6Wf3j7_T5BjniQ_6Bzj-dUC"
    BUCKET_NAME: str = "contratos"

    # Configuración de LM Studio
    LMSTUDIO_BASE: str = "http://127.0.0.1:1234/v1"
    EMBED_MODEL: str = "text-embedding-nomic-embed-text-v1.5"
    CHAT_MODEL: str = "meta-llama-3.1-8b-instruct"
    
    LMSTUDIO_API_KEY: str = "lm-studio"

    max_pages: int = 60
    chunk_chars: int = 1200
    overlap: int = 200
    top_k: int = 12
    index_batch_size: int = 64
    cache_ttl_seconds: int = 3500

    chip_prompts: dict = field(default_factory=lambda: {
        "📌 Resumen ejecutivo": "Dame un resumen ejecutivo del contrato. Incluye puntos clave, riesgos y próximos pasos.",
        "⚠️ Riesgos operativos": "Identifica riesgos operativos del contrato: mantenimiento, servicios, seguros, penalizaciones y restricciones.",
        "💰 Simulación de pagos": "Simula el flujo de pagos: renta, incrementos, indexaciones y fechas relevantes. Indica supuestos si faltan datos.",
        "✅ Checklist de obligaciones": "Genera un checklist de obligaciones del arrendatario y arrendador con evidencia (cláusulas) si aplica.",
    })

    demo_contracts: List[dict] = field(default_factory=lambda: [
        {"id": "C-001", "title": "Arrendamiento Sucursal Polanco", "state": "Ciudad de México", "expiry": "2026-06-15"},
        {"id": "C-002", "title": "Arrendamiento Bodega Monterrey", "state": "Nuevo León", "expiry": "2026-04-02"},
        {"id": "C-003", "title": "Arrendamiento Oficina Guadalajara", "state": "Jalisco", "expiry": "2026-03-28"},
    ])


SETTINGS = AppConfig()
