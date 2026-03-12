from __future__ import annotations

import os
import re
import unicodedata
import calendar
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

import pandas as pd

from core.pdf_service import PdfService
from core.storage_service import StorageService


@dataclass
class ContractMetrics:
    contrato: str
    nombre_archivo: str
    estado: Optional[str] = None
    ciudad: Optional[str] = None
    renta_mensual: Optional[float] = None
    deposito: Optional[float] = None
    superficie_m2: Optional[float] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    meses_vigencia: Optional[int] = None
    precio_m2: Optional[float] = None
    costo_total: Optional[float] = None

    # diagnóstico / validación
    texto_extraido_ok: bool = False
    posible_pdf_escaneado: bool = False
    longitud_texto: int = 0

    tiene_renta: bool = False
    tiene_deposito: bool = False
    tiene_superficie: bool = False
    tiene_estado: bool = False
    tiene_ciudad: bool = False
    tiene_fecha_inicio: bool = False
    tiene_fecha_fin: bool = False
    tiene_vigencia: bool = False
    campos_detectados: int = 0
    porcentaje_completitud: float = 0.0
    calidad_extraccion: str = "baja"


class ContractMetricsService:
    def __init__(self, storage: StorageService, pdf_service: PdfService) -> None:
        self.storage = storage
        self.pdf_service = pdf_service

        # Ojo: usamos "Estado de México" y NO "México" para evitar confundir país con estado.
        self.estados = [
            "Aguascalientes",
            "Baja California",
            "Baja California Sur",
            "Campeche",
            "Chiapas",
            "Chihuahua",
            "Ciudad de México",
            "Coahuila",
            "Colima",
            "Durango",
            "Estado de México",
            "Guanajuato",
            "Guerrero",
            "Hidalgo",
            "Jalisco",
            "Michoacán",
            "Morelos",
            "Nayarit",
            "Nuevo León",
            "Oaxaca",
            "Puebla",
            "Querétaro",
            "Quintana Roo",
            "San Luis Potosí",
            "Sinaloa",
            "Sonora",
            "Tabasco",
            "Tamaulipas",
            "Tlaxcala",
            "Veracruz",
            "Yucatán",
            "Zacatecas",
        ]

        self.meses = {
            "enero": 1,
            "febrero": 2,
            "marzo": 3,
            "abril": 4,
            "mayo": 5,
            "junio": 6,
            "julio": 7,
            "agosto": 8,
            "septiembre": 9,
            "setiembre": 9,
            "octubre": 10,
            "noviembre": 11,
            "diciembre": 12,
        }

        # ciudad -> estado
        self.city_to_state = {
            "merida": "Yucatán",
            "monterrey": "Nuevo León",
            "puebla": "Puebla",
            "queretaro": "Querétaro",
            "san juan del rio": "Querétaro",
            "guadalajara": "Jalisco",
            "leon": "Guanajuato",
            "cancun": "Quintana Roo",
            "toluca": "Estado de México",
            "gomez palacio": "Durango",
            "chihuahua": "Chihuahua",
            "colima": "Colima",
            "huehuetoca": "Estado de México",
            "juarez": "Chihuahua",
            "san luis potosi": "San Luis Potosí",
            "slp": "San Luis Potosí",
        }

    # ---------------------------------------------------------
    # Normalización
    # ---------------------------------------------------------
    @staticmethod
    def strip_accents(value: str) -> str:
        if not value:
            return ""
        return "".join(
            c for c in unicodedata.normalize("NFD", value)
            if unicodedata.category(c) != "Mn"
        )

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\u00a0", " ")
        text = self.strip_accents(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    @staticmethod
    def normalize_money(value: str) -> Optional[float]:
        if not value:
            return None
        value = value.replace(",", "").replace(" ", "").strip()
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def basename(path: str) -> str:
        return os.path.basename(path)

    def normalize_filename(self, path: str) -> str:
        base = self.basename(path)
        base = self.strip_accents(base).lower()
        return base

    # ---------------------------------------------------------
    # Diagnóstico de texto
    # ---------------------------------------------------------
    def is_text_scarce(self, text: str) -> bool:
        if not text:
            return True

        clean = text.strip()
        if len(clean) < 180:
            return True

        tokens = re.findall(r"\w+", clean)
        if len(tokens) < 40:
            return True

        return False

    # ---------------------------------------------------------
    # Helpers numéricos / fechas
    # ---------------------------------------------------------
    def _safe_date(self, year: int, month: int, day: int) -> Optional[str]:
        try:
            last_day = calendar.monthrange(year, month)[1]
            day = min(day, last_day)
            return date(year, month, day).isoformat()
        except Exception:
            return None

    def _parse_compact_date(self, value: str) -> Optional[str]:
        if not value or len(value) != 8:
            return None
        try:
            d = int(value[0:2])
            m = int(value[2:4])
            y = int(value[4:8])
            return self._safe_date(y, m, d)
        except Exception:
            return None

    def _build_iso_date(self, d: str, m: str, y: str) -> Optional[str]:
        if not d or not m or not y:
            return None

        m_norm = self.strip_accents(m).lower().strip()
        m_num = self.meses.get(m_norm)
        if not m_num:
            return None

        try:
            return self._safe_date(int(y), m_num, int(d))
        except Exception:
            return None

    # ---------------------------------------------------------
    # Extracción de renta
    # ---------------------------------------------------------
    def extract_renta_mensual(self, text: str) -> Optional[float]:
        patrones = [
            r"renta mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"la renta mensual sera de\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"pagara una renta mensual(?: establecida en este contrato)?(?: mas el i\.?v\.?a\.?)?\s*(?:de)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"contraprestacion mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"canon mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"pago mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"clausula tercera(?:.|\n){0,180}?\$([\d,]+(?:\.\d{1,2})?)",
            r"segunda\.\s*renta(?:.|\n){0,180}?\$([\d,]+(?:\.\d{1,2})?)",
            r"\brenta:\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
        ]

        candidatos: list[float] = []

        for patron in patrones:
            for m in re.finditer(patron, text, re.IGNORECASE):
                val = self.normalize_money(m.group(1))
                if val is not None:
                    candidatos.append(val)

        if candidatos:
            # Elegimos el primer candidato razonable > 1000
            for val in candidatos:
                if val >= 1000:
                    return val
            return candidatos[0]

        return None

    # ---------------------------------------------------------
    # Extracción de depósito
    # ---------------------------------------------------------
    def extract_deposito(self, text: str, renta_mensual: Optional[float]) -> Optional[float]:
        patrones_monto = [
            r"deposito(?: en garantia)?(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"deposito en garantia(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"entregara un deposito(?: en garantia)?(?: de| por)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"garantia(?: de cumplimiento)?(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
        ]

        for patron in patrones_monto:
            m = re.search(patron, text, re.IGNORECASE)
            if m:
                val = self.normalize_money(m.group(1))
                if val is not None:
                    return val

        patrones_textuales = [
            r"cantidad equivalente a una mensualidad(?: de renta)?",
            r"equivalente a una mensualidad(?: de renta)?",
            r"deposito equivalente a una mensualidad",
            r"deposito equivalente a un mes de renta",
            r"deposito equivalente a un mes",
            r"deposito equivalente a una renta mensual",
            r"un mes de renta",
        ]

        if renta_mensual is not None:
            for patron in patrones_textuales:
                if re.search(patron, text, re.IGNORECASE):
                    return renta_mensual

        return None

    # ---------------------------------------------------------
    # Extracción de superficie
    # ---------------------------------------------------------
    def extract_superficie(self, text: str) -> Optional[float]:
        patrones = [
            r"superficie total aproximada de\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"superficie aproximada de\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"superficie(?: aproximada)?\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"area(?: rentable| total| comercial)?\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"superficie:\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
        ]

        candidatos: list[float] = []

        for patron in patrones:
            for m in re.finditer(patron, text, re.IGNORECASE):
                try:
                    val = float(m.group(1))
                    # evitar capturar números absurdos pequeños tipo 1.00 m2
                    if val >= 20:
                        candidatos.append(val)
                except ValueError:
                    continue

        if candidatos:
            return candidatos[0]

        return None

    # ---------------------------------------------------------
    # Estado y ciudad
    # ---------------------------------------------------------
    def extract_estado_y_ciudad(self, text: str, path: str) -> tuple[Optional[str], Optional[str]]:
        patrones_ciudad_estado = [
            r"\bciudad\s+([A-Za-z\s]+?),\s*([A-Za-z\s]+)\b",
            r"\ben la ciudad de\s+([A-Za-z\s]+?),\s*([A-Za-z\s]+)\b",
            r"\binmueble\s+.*?ubicado\s+en\s+.*?,\s*([A-Za-z\s]+?),\s*([A-Za-z\s]+)\b",
            r"\bubicado\s+en\s+.*?,\s*([A-Za-z\s]+?),\s*([A-Za-z\s]+)\b",
        ]

        for patron in patrones_ciudad_estado:
            m = re.search(patron, text, re.IGNORECASE)
            if m:
                ciudad = self._clean_city(m.group(1))
                estado = self._match_estado(m.group(2))
                if estado:
                    return estado, ciudad

        filename = self.normalize_filename(path)

        for ciudad_norm, estado in self.city_to_state.items():
            if ciudad_norm in filename:
                return estado, self._title_city(ciudad_norm)

        text_low = self.strip_accents(text.lower())

        for estado in self.estados:
            if estado == "Estado de México":
                patron_estado = r"\bestado de mexico\b|\bedo\.?\s+de\s+mexico\b"
            else:
                estado_norm = self.strip_accents(estado.lower())
                patron_estado = r"\b" + re.escape(estado_norm) + r"\b"

            if re.search(patron_estado, text_low, re.IGNORECASE):
                return estado, None

        return None, None

    def _match_estado(self, valor: str) -> Optional[str]:
        if not valor:
            return None

        valor_norm = self.strip_accents(valor).lower().strip()

        if valor_norm in {"estado de mexico", "edo de mexico", "edomex"}:
            return "Estado de México"

        if valor_norm == "mexico":
            return None

        for e in self.estados:
            e_norm = self.strip_accents(e).lower()
            if e_norm == valor_norm:
                return e

        for e in self.estados:
            e_norm = self.strip_accents(e).lower()
            if e_norm in valor_norm or valor_norm in e_norm:
                if e == "Estado de México" and valor_norm == "mexico":
                    continue
                return e

        return None

    @staticmethod
    def _clean_city(ciudad: str) -> str:
        ciudad = ciudad.strip()
        ciudad = re.sub(r"\s+", " ", ciudad)
        return ciudad

    @staticmethod
    def _title_city(ciudad_norm: str) -> str:
        especiales = {
            "san juan del rio": "San Juan del Río",
            "gomez palacio": "Gómez Palacio",
            "san luis potosi": "San Luis Potosí",
            "ciudad de mexico": "Ciudad de México",
            "queretaro": "Querétaro",
            "merida": "Mérida",
            "cancun": "Cancún",
        }
        return especiales.get(ciudad_norm, ciudad_norm.title())

    # ---------------------------------------------------------
    # Fechas y vigencia
    # ---------------------------------------------------------
    def extract_fecha_inicio_fin(self, text: str, path: str | None = None) -> tuple[Optional[str], Optional[str]]:
        text = self.normalize_text(text)

        patrones_texto = [
            # 01 mayo 2026 al 30 abril 2036
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+al\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",

            # del 01 de mayo de 2026 al 30 de abril de 2036
            r"del\s+(\d{1,2})\s+de\s+([A-Za-z]+)\s+de\s+(\d{4})\s+al\s+(\d{1,2})\s+de\s+([A-Za-z]+)\s+de\s+(\d{4})",

            # 01.06.2024-30.06.2029
            r"(\d{2})\.(\d{2})\.(\d{4})\s*[-–]\s*(\d{2})\.(\d{2})\.(\d{4})",

            # 01/06/2024 al 30/06/2029
            r"(\d{2})/(\d{2})/(\d{4})\s+al\s+(\d{2})/(\d{2})/(\d{4})",
        ]

        for patron in patrones_texto:
            m = re.search(patron, text, re.IGNORECASE)
            if not m:
                continue

            groups = m.groups()

            # formato numérico
            if len(groups) == 6 and groups[1].isdigit() and groups[4].isdigit():
                d1, m1, y1, d2, m2, y2 = groups
                fecha_inicio = self._safe_date(int(y1), int(m1), int(d1))
                fecha_fin = self._safe_date(int(y2), int(m2), int(d2))
                return fecha_inicio, fecha_fin

            # formato textual
            if len(groups) == 6:
                d1, m1, y1, d2, m2, y2 = groups
                fecha_inicio = self._build_iso_date(d1, m1, y1)
                fecha_fin = self._build_iso_date(d2, m2, y2)
                if fecha_inicio or fecha_fin:
                    return fecha_inicio, fecha_fin

        if path:
            filename = self.normalize_filename(path)

            # 01042023 31062028
            m = re.search(r"(\d{8})\s+(\d{8})", filename)
            if m:
                fecha_inicio = self._parse_compact_date(m.group(1))
                fecha_fin = self._parse_compact_date(m.group(2))
                return fecha_inicio, fecha_fin

            # 01.06.2024-30.06.2029
            m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})[-–](\d{2})\.(\d{2})\.(\d{4})", filename)
            if m:
                d1, m1, y1, d2, m2, y2 = m.groups()
                fecha_inicio = self._safe_date(int(y1), int(m1), int(d1))
                fecha_fin = self._safe_date(int(y2), int(m2), int(d2))
                return fecha_inicio, fecha_fin

        return None, None

    def calculate_months(self, fecha_inicio: Optional[str], fecha_fin: Optional[str]) -> Optional[int]:
        if not fecha_inicio or not fecha_fin:
            return None
        try:
            f1 = pd.to_datetime(fecha_inicio)
            f2 = pd.to_datetime(fecha_fin)
            return (f2.year - f1.year) * 12 + (f2.month - f1.month) + 1
        except Exception:
            return None

    # ---------------------------------------------------------
    # Calidad
    # ---------------------------------------------------------
    @staticmethod
    def evaluate_quality(
        renta_mensual: Optional[float],
        deposito: Optional[float],
        superficie_m2: Optional[float],
        estado: Optional[str],
        fecha_inicio: Optional[str],
        fecha_fin: Optional[str],
        ciudad: Optional[str],
    ) -> tuple[int, float, str]:
        flags = [
            renta_mensual is not None,
            deposito is not None,
            superficie_m2 is not None,
            estado is not None,
            ciudad is not None,
            fecha_inicio is not None,
            fecha_fin is not None,
        ]

        encontrados = sum(flags)
        total = len(flags)
        porcentaje = round((encontrados / total) * 100, 2)

        if encontrados >= 6:
            calidad = "alta"
        elif encontrados >= 4:
            calidad = "media"
        else:
            calidad = "baja"

        return encontrados, porcentaje, calidad

    # ---------------------------------------------------------
    # Procesamiento completo
    # ---------------------------------------------------------
    def extract_metrics_from_contract(self, path: str) -> ContractMetrics:
        text = self.pdf_service.extract_full_pdf_text(path)
        text = self.normalize_text(text)

        texto_extraido_ok = not self.is_text_scarce(text)
        posible_pdf_escaneado = not texto_extraido_ok
        longitud_texto = len(text)

        renta_mensual = self.extract_renta_mensual(text)
        superficie_m2 = self.extract_superficie(text)
        estado, ciudad = self.extract_estado_y_ciudad(text, path)
        fecha_inicio, fecha_fin = self.extract_fecha_inicio_fin(text, path)
        meses_vigencia = self.calculate_months(fecha_inicio, fecha_fin)

        deposito = self.extract_deposito(text, renta_mensual)

        precio_m2 = None
        if renta_mensual is not None and superficie_m2 not in (None, 0):
            precio_m2 = renta_mensual / superficie_m2

        costo_total = None
        if renta_mensual is not None and meses_vigencia is not None:
            costo_total = renta_mensual * meses_vigencia

        campos_detectados, porcentaje_completitud, calidad = self.evaluate_quality(
            renta_mensual=renta_mensual,
            deposito=deposito,
            superficie_m2=superficie_m2,
            estado=estado,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            ciudad=ciudad,
        )

        return ContractMetrics(
            contrato=path,
            nombre_archivo=self.basename(path),
            estado=estado,
            ciudad=ciudad,
            renta_mensual=renta_mensual,
            deposito=deposito,
            superficie_m2=superficie_m2,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            meses_vigencia=meses_vigencia,
            precio_m2=precio_m2,
            costo_total=costo_total,
            texto_extraido_ok=texto_extraido_ok,
            posible_pdf_escaneado=posible_pdf_escaneado,
            longitud_texto=longitud_texto,
            tiene_renta=renta_mensual is not None,
            tiene_deposito=deposito is not None,
            tiene_superficie=superficie_m2 is not None,
            tiene_estado=estado is not None,
            tiene_ciudad=ciudad is not None,
            tiene_fecha_inicio=fecha_inicio is not None,
            tiene_fecha_fin=fecha_fin is not None,
            tiene_vigencia=meses_vigencia is not None,
            campos_detectados=campos_detectados,
            porcentaje_completitud=porcentaje_completitud,
            calidad_extraccion=calidad,
        )

    # ---------------------------------------------------------
    # Dataset completo
    # ---------------------------------------------------------
    def build_contracts_dataframe(self, paths: list[str]) -> pd.DataFrame:
        rows = []

        for path in paths:
            try:
                metrics = self.extract_metrics_from_contract(path)
                rows.append(asdict(metrics))
            except Exception:
                continue

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
            "texto_extraido_ok",
            "posible_pdf_escaneado",
            "longitud_texto",
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
            "calidad_extraccion",
        ]

        if not rows:
            return pd.DataFrame(columns=columnas)

        return pd.DataFrame(rows)