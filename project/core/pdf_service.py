from __future__ import annotations

import io
import os
import re
import shutil
from typing import Optional

import fitz
from PIL import Image, ImageFilter, ImageOps

from core.storage_service import StorageService


class PdfService:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage
        self._ocr_ready = False
        self._init_ocr()

        self.estados_mexico = [
            "aguascalientes", "baja california", "baja california sur", "campeche",
            "chiapas", "chihuahua", "ciudad de mexico", "coahuila", "colima",
            "durango", "guanajuato", "guerrero", "hidalgo", "jalisco", "mexico",
            "michoacan", "morelos", "nayarit", "nuevo leon", "oaxaca", "puebla",
            "queretaro", "quintana roo", "san luis potosi", "sinaloa", "sonora",
            "tabasco", "tamaulipas", "tlaxcala", "veracruz", "yucatan", "zacatecas"
        ]

    # ---------------------------------------------------------
    # OCR setup
    # ---------------------------------------------------------
    def _init_ocr(self) -> None:
        try:
            import pytesseract

            tesseract_bin = shutil.which("tesseract")

            if not tesseract_bin and os.path.exists("/opt/homebrew/bin/tesseract"):
                tesseract_bin = "/opt/homebrew/bin/tesseract"

            if not tesseract_bin and os.path.exists("/usr/local/bin/tesseract"):
                tesseract_bin = "/usr/local/bin/tesseract"

            if tesseract_bin:
                pytesseract.pytesseract.tesseract_cmd = tesseract_bin
                self._ocr_ready = True
            else:
                self._ocr_ready = False

        except Exception:
            self._ocr_ready = False
    
    @staticmethod
    def normalize_name(value: str) -> str:
        value = (value or "").lower().strip()
        value = value.replace("á", "a").replace("é", "e").replace("í", "i")
        value = value.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        return value
    
    @staticmethod
    def unique_preserve_order(items: list[Optional[str]]) -> list[str]:
        seen = set()
        result: list[str] = []
        for item in items:
            if not item:
                continue
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _is_state_code_pdf(self, path: str) -> bool:
        base = self.normalize_name(os.path.basename(path))
        no_ext = base.replace(".pdf", "")

        if no_ext in self.estados_mexico:
            return True

        full = self.normalize_name(path)
        for estado in self.estados_mexico:
            if full.endswith(f"/{estado}.pdf"):
                return True

        return False

    def _is_federal_code_pdf(self, path: str) -> bool:
        full = self.normalize_name(path)
        patrones = [
            "codigo civil federal",
            "codigo_civil_federal",
            "codigocivilfederal",
            "federal.pdf",
        ]
        return any(p in full for p in patrones)

    def find_codigo_civil_federal(self, pdf_paths: list[str]) -> Optional[str]:
        if not pdf_paths:
            return None

        # Primero intenta coincidencias más específicas
        scored: list[tuple[int, str]] = []
        for path in pdf_paths:
            norm = self.normalize_name(path)
            score = 0
            if "codigo civil federal" in norm or "codigo_civil_federal" in norm:
                score += 100
            if os.path.basename(norm) == "federal.pdf":
                score += 80
            if "federal" in norm:
                score += 20
            if "codigo" in norm and "civil" in norm:
                score += 20
            if score > 0:
                scored.append((score, path))

        if scored:
            scored.sort(key=lambda x: (-x[0], x[1]))
            return scored[0][1]

        # Fallback: usa la heurística general
        for path in pdf_paths:
            if self._is_federal_code_pdf(path):
                return path

        return None

    def find_codigos_civiles_estatales(self, pdf_paths: list[str]) -> list[str]:
        if not pdf_paths:
            return []

        result = []
        for path in pdf_paths:
            norm = self.normalize_name(path)
            if self._is_federal_code_pdf(path):
                continue
            if self._is_state_code_pdf(path):
                result.append(path)
                continue
            if "codigo civil" in norm or "codigo_civil" in norm or "código civil" in path.lower():
                result.append(path)

        return sorted(set(result))

    # ---------------------------------------------------------
    # Utilidades de texto
    # ---------------------------------------------------------
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()

    @staticmethod
    def _is_sparse_text(text: str) -> bool:
        if not text:
            return True

        text = text.strip()
        if len(text) < 140:
            return True

        tokens = re.findall(r"\w+", text)
        if len(tokens) < 30:
            return True

        return False

    @staticmethod
    def _normalize_ocr_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\u00a0", " ")
        text = text.replace("|", "I")
        text = text.replace("ﬁ", "fi")
        text = text.replace("ﬂ", "fl")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()

    # ---------------------------------------------------------
    # OCR helpers
    # ---------------------------------------------------------
    @staticmethod
    def _page_to_pil_image(page: fitz.Page, zoom: float = 1.8) -> Image.Image:
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.open(io.BytesIO(pix.tobytes("png")))

    @staticmethod
    def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
        img = img.convert("L")
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.SHARPEN)
        img = img.point(lambda x: 255 if x > 170 else 0)
        img = ImageOps.expand(img, border=8, fill=255)
        return img

    def _ocr_page(self, page: fitz.Page) -> str:
        if not self._ocr_ready:
            return ""

        try:
            import pytesseract

            img = self._page_to_pil_image(page, zoom=1.8)
            img = self._preprocess_for_ocr(img)

            candidates = []
            for psm in ("6", "4"):
                try:
                    txt = pytesseract.image_to_string(
                        img,
                        lang="eng",
                        config=f"--psm {psm}"
                    )
                    txt = self._normalize_ocr_text(txt)
                    candidates.append(txt)
                except Exception:
                    continue

            if not candidates:
                return ""

            return max(candidates, key=len)

        except Exception:
            return ""

    # ---------------------------------------------------------
    # Heurística de velocidad
    # ---------------------------------------------------------
    def _max_pages_for_dashboard(self, path: str, max_pages: int) -> int:
        base = os.path.basename(path).lower()

        if base.startswith("t"):
            return min(max_pages, 4)

        if "avanzado" in base:
            return min(max_pages, 3)

        if "contrato" in base or re.match(r"^c\d+", base):
            return min(max_pages, 3)

        return min(max_pages, 2)

    def _should_force_ocr(self, path: str) -> bool:
        base = os.path.basename(path).lower()
        return base.startswith("t")

    # ---------------------------------------------------------
    # Extracción por páginas
    # ---------------------------------------------------------
    def pdf_bytes_to_pages(self, pdf_bytes: bytes, path: str, max_pages: int) -> list[tuple[int, str]]:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages: list[tuple[int, str]] = []

        page_limit = self._max_pages_for_dashboard(path, max_pages)
        force_ocr = self._should_force_ocr(path)

        for i in range(min(len(doc), page_limit)):
            page = doc[i]

            text_normal = page.get_text("text")
            text_normal = self.clean_text(text_normal)

            text_final = text_normal

            # OCR solo cuando de verdad vale la pena
            if force_ocr or self._is_sparse_text(text_normal):
                ocr_text = self._ocr_page(page)
                if len(ocr_text) > len(text_normal):
                    text_final = self.clean_text(ocr_text)

            if text_final:
                pages.append((i + 1, text_final))

        return pages

    # ---------------------------------------------------------
    # Extracción completa
    # ---------------------------------------------------------
    def extract_full_pdf_text(self, path: str, max_pages: int = 4) -> str:
        try:
            pdf_bytes = self.storage.download(path)
            pages = self.pdf_bytes_to_pages(pdf_bytes, path=path, max_pages=max_pages)
            return "\n\n".join(
                [f"[Página {page_num}]\n{text}" for page_num, text in pages if text]
            )
        except Exception:
            return ""

    # ---------------------------------------------------------
    # Chunking
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # RAG
    # ---------------------------------------------------------
    def build_docs_from_files(
        self,
        file_paths: tuple[str, ...],
        max_pages: int,
        chunk_chars: int,
        overlap: int
    ) -> list[dict]:
        docs = []

        for path in file_paths:
            try:
                pdf_bytes = self.storage.download(path)
            except Exception:
                continue

            pages = self.pdf_bytes_to_pages(pdf_bytes, path=path, max_pages=max_pages)

            for page_num, page_text in pages:
                for chunk_id, chunk in enumerate(self.chunk_text(page_text, chunk_chars, overlap)):
                    docs.append(
                        {
                            "file": path,
                            "page": page_num,
                            "chunk": chunk_id,
                            "text": chunk,
                        }
                    )

        return docs