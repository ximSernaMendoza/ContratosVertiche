from __future__ import annotations

import os
import re
from typing import Optional
from supabase import create_client
from config.settings import SETTINGS


class StorageService:
    def __init__(self) -> None:
        self.client = create_client(SETTINGS.SUPABASE_URL, SETTINGS.SUPABASE_KEY)
        self.bucket = self.client.storage.from_(SETTINGS.BUCKET_NAME)

    def create_signed_url(self, filename: str, seconds: int = 3600) -> str:
        try:
            resp = self.bucket.create_signed_url(filename, seconds)
            return resp.get("signedURL") or resp.get("signedUrl") or ""
        except Exception:
            return ""

    def download(self, path: str) -> bytes:
        return self.bucket.download(path)

    def upload(self, file_bytes: bytes, dest_path: str, content_type: Optional[str] = None):
        opts = {"content-type": content_type} if content_type else {}
        return self.bucket.upload(dest_path, file_bytes, file_options=opts)

    def list_all_pdfs(self, prefix: str = "") -> list[str]:
        """
        Lista TODOS los PDFs del bucket (incluyendo subcarpetas).
        Regresa paths tipo: 'Colima/C02_Contrato_Colima-02.pdf'
        """
        pdfs = []
        stack = [prefix.strip("/")] if prefix else [""]

        while stack:
            cur = stack.pop()
            items = self.bucket.list(path=cur)

            for it in items or []:
                name = it.get("name", "")
                if not name:
                    continue

                # Supabase Storage list() regresa nombres relativos al path consultado
                full = f"{cur}/{name}".strip("/") if cur else name

                # Si es carpeta, la exploramos (en Supabase suele venir sin ".pdf")
                if not name.lower().endswith(".pdf"):
                    # heurística simple: si no trae extensión, lo tratamos como folder
                    # (si en tu bucket hay archivos sin extensión, dímelo y ajustamos)
                    stack.append(full)
                    continue

                pdfs.append(full)

        # quita duplicados y ordena
        return sorted(set(pdfs))

    def list_root_files(self) -> list[str]:
        items = self.bucket.list(path="")
        return sorted([it.get("name") for it in (items or []) if it.get("name")])

    @staticmethod
    def safe_filename(name: str) -> str:
        name = name.replace("\\", "/").split("/")[-1]
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
        return name or "upload.bin"

    @staticmethod
    def basename(path: str) -> str:
        return os.path.basename(path)
