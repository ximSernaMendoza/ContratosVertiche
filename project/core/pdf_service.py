from __future__ import annotations

import fitz
import re
from typing import Optional
from core.storage_service import StorageService
import os


class PdfService:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    @staticmethod
    def pdf_bytes_to_pages(pdf_bytes: bytes, max_pages: int) -> list[tuple[int, str]]:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for i in range(min(len(doc), max_pages)):
            t = doc[i].get_text("text").strip()
            if t:
                pages.append((i + 1, t))
        return pages

    @staticmethod
    def clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def chunk_text(self, text: str, chunk_chars: int, overlap: int) -> list[str]:
        text = self.clean_text(text)
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_chars)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = max(0, end - overlap)
        return chunks

    def extract_full_pdf_text(self, path: str, max_pages: int = 200) -> str:
        try:
            pdf_bytes = self.storage.download(path)
            pages = self.pdf_bytes_to_pages(pdf_bytes, max_pages=max_pages)
            return "\n\n".join(
                [f"[Página {page_num}]\n{text}" for page_num, text in pages if text]
            )
        except Exception:
            return ""

    def build_docs_from_files(self, file_paths: tuple[str, ...], max_pages: int, chunk_chars: int, overlap: int) -> list[dict]:
        docs = []
        for path in file_paths:
            try:
                pdf_bytes = self.storage.download(path)
            except Exception:
                continue
            pages = self.pdf_bytes_to_pages(pdf_bytes, max_pages)
            for page_num, page_text in pages:
                for chunk_id, chunk in enumerate(self.chunk_text(page_text, chunk_chars, overlap)):
                    docs.append({"file": path, "page": page_num, "chunk": chunk_id, "text": chunk})
        return docs

    # Código Civil Federal (siempre obligatorio)
    def find_codigo_civil_federal(self, all_pdfs: list[str]) -> Optional[str]:
        """
        Busca el Código Civil Federal.
        Debe existir un archivo con 'federal' en el nombre.
        """
        preferred_patterns = [
            "codigo civil federal",
            "código civil federal",
            "codigo_civil_federal",
            "codigocivilfederal",
            "federal",
        ]

        normalized = []
        for p in all_pdfs:
            base = os.path.basename(p).lower()
            normalized.append((p, base))

        for full_path, base in normalized:
            if any(pat in base for pat in preferred_patterns):
                return full_path

        return None
    
    # Códigos Civiles Estatales
    def find_codigos_civiles_estatales(self, all_pdfs: list[str]) -> list[str]:
        """
        Devuelve los PDFs que probablemente correspondan a códigos civiles estatales.

        Heurísticas:
        - Excluye el Código Civil Federal.
        - Excluye contratos.
        - Acepta archivos cuyo path o nombre sugiera que son códigos estatales,
        por ejemplo:
            Colima/Colima.pdf
            Jalisco/Codigo_Civil_Jalisco.pdf
            codigos/estados/Colima.pdf
        """

        estados_mexico = [
            "aguascalientes", "baja california", "baja california sur", "campeche",
            "chiapas", "chihuahua", "ciudad de mexico", "coahuila", "colima",
            "durango", "guanajuato", "guerrero", "hidalgo", "jalisco", "mexico",
            "michoacan", "morelos", "nayarit", "nuevo leon", "oaxaca", "puebla",
            "queretaro", "quintana roo", "san luis potosi", "sinaloa", "sonora",
            "tabasco", "tamaulipas", "tlaxcala", "veracruz", "yucatan", "zacatecas"
        ]

        state_codes = []

        for p in all_pdfs:
            full_path = p.lower()
            base_name = os.path.basename(p).lower()

            # excluir federal
            if "federal" in full_path:
                continue

            # excluir contratos
            if "contrato" in full_path:
                continue

            # caso 1: nombre/path contiene explícitamente "codigo civil"
            if (
                "codigo civil" in full_path
                or "código civil" in full_path
                or "codigo_civil" in full_path
            ):
                state_codes.append(p)
                continue

            # caso 2: heurística por carpeta o archivo con nombre de estado
            for estado in estados_mexico:
                estado_slug = estado.replace(" ", "_")
                estado_dash = estado.replace(" ", "-")

                if (
                    f"/{estado}/" in full_path
                    or f"/{estado_slug}/" in full_path
                    or f"/{estado_dash}/" in full_path
                    or base_name == f"{estado}.pdf"
                    or base_name == f"{estado_slug}.pdf"
                    or base_name == f"{estado_dash}.pdf"
                ):
                    state_codes.append(p)
                    break

        return sorted(set(state_codes))

    @staticmethod
    def unique_preserve_order(items: list[str]) -> list[str]:
        seen = set()
        out = []
        for x in items:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out
