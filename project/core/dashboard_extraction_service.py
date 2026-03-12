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
class DashboardContractRecord:
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

    fuente_estado: Optional[str] = None
    fuente_ciudad: Optional[str] = None
    fuente_renta: Optional[str] = None
    fuente_deposito: Optional[str] = None
    fuente_superficie: Optional[str] = None
    fuente_fechas: Optional[str] = None

    texto_extraido_ok: bool = False
    posible_pdf_escaneado: bool = False
    longitud_texto: int = 0
    confianza_dashboard: str = "baja"

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


class DashboardExtractionService:
    def __init__(self, storage: StorageService, pdf_service: PdfService) -> None:
        self.storage = storage
        self.pdf_service = pdf_service

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
            "vallarta": "Jalisco",
            "puerto vallarta": "Jalisco",
            "cachanilla": "Baja California",
            "mexicali": "Baja California",
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

        # Arregla texto roto tipo "R e n t a"
        text = re.sub(r"(?<=\b[A-Za-z])\s(?=[A-Za-z]\b)", "", text)

        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        text = text.replace("|", "I")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n", text)

        return text.strip()

    def normalize_filename(self, path: str) -> str:
        base = os.path.basename(path)
        base = self.strip_accents(base).lower()
        return base

    @staticmethod
    def basename(path: str) -> str:
        return os.path.basename(path)

    @staticmethod
    def normalize_money(value: str) -> Optional[float]:
        if not value:
            return None
        value = value.replace(",", "").replace(" ", "").strip()
        try:
            return float(value)
        except ValueError:
            return None

    # ---------------------------------------------------------
    # Texto del contrato
    # ---------------------------------------------------------
    def _extract_text(self, path: str) -> tuple[str, bool, bool, int]:
        text = self.pdf_service.extract_full_pdf_text(path, max_pages=5)
        text = self.normalize_text(text)

        longitud = len(text)
        texto_extraido_ok = longitud >= 180 and len(re.findall(r"\w+", text)) >= 40
        posible_pdf_escaneado = not texto_extraido_ok

        return text, texto_extraido_ok, posible_pdf_escaneado, longitud

    # ---------------------------------------------------------
    # Helpers de fechas
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
        m_norm = self.strip_accents(m).lower().strip()
        m_num = self.meses.get(m_norm)
        if not m_num:
            return None
        try:
            return self._safe_date(int(y), m_num, int(d))
        except Exception:
            return None

    def _calculate_months(self, fecha_inicio: Optional[str], fecha_fin: Optional[str]) -> Optional[int]:
        if not fecha_inicio or not fecha_fin:
            return None
        try:
            f1 = pd.to_datetime(fecha_inicio)
            f2 = pd.to_datetime(fecha_fin)
            return (f2.year - f1.year) * 12 + (f2.month - f1.month) + 1
        except Exception:
            return None

    def _infer_start_from_end_and_years(self, fecha_fin: str, years: int) -> Optional[str]:
        try:
            f_fin = pd.to_datetime(fecha_fin)
            y = f_fin.year - years
            m = f_fin.month
            d = f_fin.day + 1

            last_day = calendar.monthrange(y, m)[1]
            if d > last_day:
                d = last_day

            return date(y, m, d).isoformat()
        except Exception:
            return None

    # ---------------------------------------------------------
    # Helpers de contexto
    # ---------------------------------------------------------
    def _near_keywords(
        self,
        text: str,
        positive_keywords: list[str],
        negative_keywords: list[str] | None = None,
        window_before: int = 50,
        window_after: int = 220,
    ) -> list[str]:
        negative_keywords = negative_keywords or []
        text_low = text.lower()
        snippets = []

        for kw in positive_keywords:
            for m_kw in re.finditer(re.escape(kw.lower()), text_low, re.IGNORECASE):
                start = max(0, m_kw.start() - window_before)
                end = min(len(text), m_kw.end() + window_after)
                snippet = text[start:end]
                snippet_low = snippet.lower()

                if any(neg.lower() in snippet_low for neg in negative_keywords):
                    continue

                snippets.append(snippet)

        return snippets

    def _extract_best_money_from_snippets(
        self,
        snippets: list[str],
        min_val: float = 1000,
        max_val: float = 10000000,
    ) -> Optional[float]:
        money_pattern = r"\$?\s*([\d,]+(?:\.\d{1,2})?)"
        candidates: list[tuple[float, int]] = []

        for snippet in snippets:
            for m in re.finditer(money_pattern, snippet, re.IGNORECASE):
                val = self.normalize_money(m.group(1))
                if val is None:
                    continue
                if not (min_val <= val <= max_val):
                    continue

                raw = m.group(1).replace(",", "").strip()

                # Evita años como 2025
                if re.fullmatch(r"20\d{2}", raw):
                    continue

                candidates.append((val, m.start()))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    # ---------------------------------------------------------
    # Estado y ciudad
    # ---------------------------------------------------------
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
            "vallarta": "Puerto Vallarta",
        }
        return especiales.get(ciudad_norm, ciudad_norm.title())

    def extract_estado_y_ciudad(
        self, text: str, path: str
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        filename = self.normalize_filename(path)

        # En T... el nombre del archivo suele ser más confiable
        if filename.startswith("t"):
            for ciudad_norm, estado in self.city_to_state.items():
                if ciudad_norm in filename:
                    return estado, self._title_city(ciudad_norm), "nombre_archivo", "nombre_archivo"

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
                    return estado, ciudad, "texto", "texto"

        for ciudad_norm, estado in self.city_to_state.items():
            if ciudad_norm in filename:
                return estado, self._title_city(ciudad_norm), "nombre_archivo", "nombre_archivo"

        text_low = self.strip_accents(text.lower())
        for estado in self.estados:
            if estado == "Estado de México":
                patron_estado = r"\bestado de mexico\b|\bedo\.?\s+de\s+mexico\b"
            else:
                estado_norm = self.strip_accents(estado.lower())
                patron_estado = r"\b" + re.escape(estado_norm) + r"\b"

            if re.search(patron_estado, text_low, re.IGNORECASE):
                return estado, None, "texto", None

        return None, None, None, None

    # ---------------------------------------------------------
    # Fechas
    # ---------------------------------------------------------
    def extract_fechas(
        self, text: str, path: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        patrones_texto = [
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+al\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
            r"del\s+(\d{1,2})\s+de\s+([A-Za-z]+)\s+de\s+(\d{4})\s+al\s+(\d{1,2})\s+de\s+([A-Za-z]+)\s+de\s+(\d{4})",
            r"(\d{2})\.(\d{2})\.(\d{4})\s*[-–]\s*(\d{2})\.(\d{2})\.(\d{4})",
            r"(\d{2})/(\d{2})/(\d{4})\s+al\s+(\d{2})/(\d{2})/(\d{4})",
        ]

        for patron in patrones_texto:
            m = re.search(patron, text, re.IGNORECASE)
            if not m:
                continue

            groups = m.groups()

            if len(groups) == 6 and groups[1].isdigit() and groups[4].isdigit():
                d1, m1, y1, d2, m2, y2 = groups
                return (
                    self._safe_date(int(y1), int(m1), int(d1)),
                    self._safe_date(int(y2), int(m2), int(d2)),
                    "texto",
                )

            if len(groups) == 6:
                d1, m1, y1, d2, m2, y2 = groups
                return (
                    self._build_iso_date(d1, m1, y1),
                    self._build_iso_date(d2, m2, y2),
                    "texto",
                )

        # Vigencia en años + fecha final
        m_years = re.search(
            r"(?:plazo inicial de|vigencia de|duracion de|plazo de)\s*(\d+)\s*anos",
            text,
            re.IGNORECASE,
        )
        m_end = re.search(
            r"(?:concluyendo(?: el dia)?|hasta el dia|terminando el dia)\s*(\d{1,2})\s+de\s+([A-Za-z]+)\s+(?:del\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if m_years and m_end:
            years = int(m_years.group(1))
            d2, m2, y2 = m_end.groups()
            fecha_fin = self._build_iso_date(d2, m2, y2)
            if fecha_fin:
                fecha_inicio = self._infer_start_from_end_and_years(fecha_fin, years)
                return fecha_inicio, fecha_fin, "inferido_texto"

        filename = self.normalize_filename(path)

        # 01042023 31062028
        m = re.search(r"(\d{8})\s+(\d{8})", filename)
        if m:
            return (
                self._parse_compact_date(m.group(1)),
                self._parse_compact_date(m.group(2)),
                "nombre_archivo",
            )

        # 01.06.2024-30.06.2029
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})[-–](\d{2})\.(\d{2})\.(\d{4})", filename)
        if m:
            d1, m1, y1, d2, m2, y2 = m.groups()
            return (
                self._safe_date(int(y1), int(m1), int(d1)),
                self._safe_date(int(y2), int(m2), int(d2)),
                "nombre_archivo",
            )

        return None, None, None

    # ---------------------------------------------------------
    # Renta
    # ---------------------------------------------------------
    def extract_renta(self, text: str) -> tuple[Optional[float], Optional[str]]:
        patrones_directos = [
            r"renta mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"la renta mensual sera de\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"pagara una renta mensual(?: establecida en este contrato)?(?: mas el i\.?v\.?a\.?)?\s*(?:de)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"contraprestacion mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"canon mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"pago mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"mensualidad(?: de renta)?(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"por concepto de renta mensual(?: sera| de|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"\brenta:\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
        ]

        for patron in patrones_directos:
            m = re.search(patron, text, re.IGNORECASE)
            if m:
                val = self.normalize_money(m.group(1))
                if val is not None and 1000 <= val <= 10000000:
                    return val, "texto"

        snippets = self._near_keywords(
            text=text,
            positive_keywords=[
                "renta mensual",
                "renta",
                "contraprestacion mensual",
                "contraprestacion",
                "canon mensual",
                "pago mensual",
                "mensualidad",
            ],
            negative_keywords=["deposito", "garantia", "pena", "multa"],
            window_before=40,
            window_after=180,
        )

        val = self._extract_best_money_from_snippets(snippets)
        if val is not None:
            return val, "texto_contexto"

        return None, None

    # ---------------------------------------------------------
    # Depósito
    # ---------------------------------------------------------
    def extract_deposito(self, text: str, renta_mensual: Optional[float]) -> tuple[Optional[float], Optional[str]]:
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
                if val is not None and val >= 1000:
                    return val, "texto"

        snippets = self._near_keywords(
            text=text,
            positive_keywords=[
                "deposito",
                "deposito en garantia",
                "deposito de garantia",
                "garantia",
                "mes de garantia",
            ],
            negative_keywords=["pena", "multa"],
            window_before=40,
            window_after=220,
        )

        val = self._extract_best_money_from_snippets(snippets, min_val=1000)
        if val is not None:
            return val, "texto_contexto"

        patrones_textuales = [
            r"cantidad equivalente a una mensualidad(?: de renta)?",
            r"equivalente a una mensualidad(?: de renta)?",
            r"deposito equivalente a una mensualidad",
            r"deposito equivalente a un mes de renta",
            r"deposito equivalente a un mes",
            r"deposito equivalente a una renta mensual",
            r"un mes de renta",
            r"como deposito una mensualidad",
            r"como deposito en garantia una mensualidad",
            r"una mensualidad como deposito",
            r"una mensualidad como deposito en garantia",
            r"una mensualidad como garantia",
            r"mes de renta como deposito",
        ]

        if renta_mensual is not None:
            for patron in patrones_textuales:
                if re.search(patron, text, re.IGNORECASE):
                    return renta_mensual, "inferido_desde_renta"

        return None, None

    # ---------------------------------------------------------
    # Superficie
    # ---------------------------------------------------------
    def extract_superficie(self, text: str) -> tuple[Optional[float], Optional[str]]:
        patrones = [
            r"superficie rentable total aproximada de\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"superficie total aproximada de\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"superficie aproximada de\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"superficie(?: aproximada)?\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"area comercial(?: de)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"area rentable(?: total)?(?: de)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"area(?: rentable| total| comercial)?\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
            r"superficie:\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros cuadrados)",
        ]

        for patron in patrones:
            m = re.search(patron, text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 20 <= val <= 100000:
                        return val, "texto"
                except ValueError:
                    pass

        patrones_contexto = [
            r"(superficie|area|area comercial|area rentable|metros cuadrados)(?:.|\n){0,180}?(\d+(?:\.\d+)?)\s*(m²|m2|metros cuadrados)",
            r"(\d+(?:\.\d+)?)\s*(m²|m2|metros cuadrados)(?:.|\n){0,120}?(superficie|area|local|inmueble|rentable)",
        ]

        for patron in patrones_contexto:
            m_ctx = re.search(patron, text, re.IGNORECASE)
            if m_ctx:
                try:
                    nums = [g for g in m_ctx.groups() if g and re.fullmatch(r"\d+(?:\.\d+)?", str(g))]
                    if nums:
                        val = float(nums[0])
                        if 20 <= val <= 100000:
                            return val, "texto_contexto"
                except ValueError:
                    pass

        candidatos = []
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(m²|m2|metros cuadrados)", text, re.IGNORECASE):
            try:
                val = float(m.group(1))
                if 20 <= val <= 100000:
                    candidatos.append(val)
            except ValueError:
                continue

        if candidatos:
            return max(candidatos), "texto"

        return None, None

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
    ) -> tuple[int, float]:
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

        return encontrados, porcentaje

    # ---------------------------------------------------------
    # Extracción completa
    # ---------------------------------------------------------
    def extract_contract_record(self, path: str) -> DashboardContractRecord:
        text, texto_extraido_ok, posible_pdf_escaneado, longitud_texto = self._extract_text(path)

        renta_mensual, fuente_renta = self.extract_renta(text)
        superficie_m2, fuente_superficie = self.extract_superficie(text)
        estado, ciudad, fuente_estado, fuente_ciudad = self.extract_estado_y_ciudad(text, path)
        fecha_inicio, fecha_fin, fuente_fechas = self.extract_fechas(text, path)
        meses_vigencia = self._calculate_months(fecha_inicio, fecha_fin)
        deposito, fuente_deposito = self.extract_deposito(text, renta_mensual)

        # Inferencia extra: si no hay renta pero sí depósito y el texto sugiere 2 meses
        if renta_mensual is None and deposito is not None:
            if re.search(r"dos mensualidades|equivalente a dos meses|2 meses de renta", text, re.IGNORECASE):
                renta_mensual = deposito / 2
                fuente_renta = "inferido_desde_deposito"

        precio_m2 = None
        if renta_mensual is not None and superficie_m2 not in (None, 0):
            precio_m2 = renta_mensual / superficie_m2

        costo_total = None
        if renta_mensual is not None and meses_vigencia is not None:
            costo_total = renta_mensual * meses_vigencia

        campos_detectados, porcentaje_completitud = self.evaluate_quality(
            renta_mensual=renta_mensual,
            deposito=deposito,
            superficie_m2=superficie_m2,
            estado=estado,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            ciudad=ciudad,
        )

        confianza = "baja"
        if campos_detectados >= 6 and texto_extraido_ok:
            confianza = "alta"
        elif campos_detectados >= 4:
            confianza = "media"

        return DashboardContractRecord(
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
            fuente_estado=fuente_estado,
            fuente_ciudad=fuente_ciudad,
            fuente_renta=fuente_renta,
            fuente_deposito=fuente_deposito,
            fuente_superficie=fuente_superficie,
            fuente_fechas=fuente_fechas,
            texto_extraido_ok=texto_extraido_ok,
            posible_pdf_escaneado=posible_pdf_escaneado,
            longitud_texto=longitud_texto,
            confianza_dashboard=confianza,
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
        )

    # ---------------------------------------------------------
    # Dataframe final
    # ---------------------------------------------------------
    def build_dashboard_dataframe(self, paths: list[str]) -> pd.DataFrame:
        rows = []

        for path in paths:
            try:
                record = self.extract_contract_record(path)
                rows.append(asdict(record))
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
            "fuente_estado",
            "fuente_ciudad",
            "fuente_renta",
            "fuente_deposito",
            "fuente_superficie",
            "fuente_fechas",
            "texto_extraido_ok",
            "posible_pdf_escaneado",
            "longitud_texto",
            "confianza_dashboard",
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
        ]

        if not rows:
            return pd.DataFrame(columns=columnas)

        return pd.DataFrame(rows)