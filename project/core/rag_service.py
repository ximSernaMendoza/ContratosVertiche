from __future__ import annotations
import os
import re
import numpy as np
import streamlit as st
from openai import OpenAI
from config.settings import SETTINGS
from core.pdf_service import PdfService
from typing import Optional

class RagService:
    def __init__(self, pdf_service: PdfService) -> None:
        self.pdf_service = pdf_service
        self.client = OpenAI(base_url=SETTINGS.LMSTUDIO_BASE, api_key=SETTINGS.LMSTUDIO_API_KEY)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        resp = self.client.embeddings.create(model=SETTINGS.EMBED_MODEL, input=texts)
        return np.array([d.embedding for d in resp.data], dtype=np.float32)

    @staticmethod
    def cosine_sim_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
        return a_norm @ b_norm.T

    @st.cache_resource(show_spinner=True)
    def build_index(_self, max_pages: int, chunk_chars: int, overlap: int, files_to_index: Optional[tuple[str, ...]] = None,):
        if _self.pdf_service.storage.bucket is None:
            return [], np.zeros((0, 1), dtype=np.float32)

        all_files = _self.pdf_service.storage.list_all_pdfs()
        pdf_files = list(files_to_index) if files_to_index else all_files

        docs, texts = [], []

        for path in pdf_files:
            try:
                pdf_bytes = _self.pdf_service.storage.bucket.download(path)
            except Exception:
                continue

            pages = _self.pdf_service.pdf_bytes_to_pages(pdf_bytes, max_pages)
            for page_num, page_text in pages:
                for ci, chunk in enumerate(
                    _self.pdf_service.chunk_text(page_text, chunk_chars, overlap)
                ):
                    docs.append(
                        {
                            "file": path,
                            "page": page_num,
                            "chunk": ci,
                            "text": chunk,
                        }
                    )
                    texts.append(chunk)

        if not texts:
            return [], np.zeros((0, 1), dtype=np.float32)

        embs = []
        for i in range(0, len(texts), 64):
            embs.append(_self.embed_texts(texts[i:i + 64]))

        return docs, np.vstack(embs)
    
    def retrieve_context(
        self,
        question: str,
        docs,
        doc_embs,
        k: int,
        allowed_files: Optional[set[str]] = None,
    ):
        if len(docs) == 0 or getattr(doc_embs, "size", 0) == 0:
            return "", []

        q_emb = self.embed_texts([question])
        sims = self.cosine_sim_matrix(doc_embs, q_emb).reshape(-1)

        idx = np.arange(len(docs))
        if allowed_files:
            mask = np.array([d["file"] in allowed_files for d in docs], dtype=bool)
            idx = idx[mask]
            sims = sims[mask]

        if len(idx) == 0:
            return "", []

        top_local = np.argsort(-sims)[:k]
        top_idx = idx[top_local]

        selected = [docs[int(i)] for i in top_idx]
        context = "\n\n".join(
            [f"Source: {d['file']} (page {d['page']}, chunk {d['chunk']})\n{d['text']}"
            for d in selected]
        )
        return context, selected

    def retrieve_context_with_neighbors(self, question: str, docs: list[dict], doc_embs: np.ndarray, k: int, allowed_files: Optional[set[str]] = None, neighbor_radius: int = 1):
        """
        Recupera top-k por embeddings y además agrega vecinos (chunks cercanos)
        para evitar perder la frase exacta que responde.
        SIN keywords. Esto mejora para cualquier pregunta.
        """
        if len(docs) == 0 or getattr(doc_embs, "size", 0) == 0:
            return "", []
        
        q_emb = self.embed_texts([question])
        sims = self.cosine_sim_matrix(doc_embs, q_emb).reshape(-1)

        idx = np.arange(len(docs))
        if allowed_files:
            mask = np.array([d["file"] in allowed_files for d in docs], dtype=bool)
            idx = idx[mask]
            sims = sims[mask]

        top_local = np.argsort(-sims)[:k]
        top_idx = idx[top_local].tolist()

        # Agregar vecinos por (file,page) y chunk +/- radius
        want = set(top_idx)
        # índice rápido: (file,page,chunk)->global_i
        pos2i = {(d["file"], d["page"], d["chunk"]): i for i, d in enumerate(docs)}

        for gi in top_idx:
            d = docs[int(gi)]
            for delta in range(-neighbor_radius, neighbor_radius + 1):
                if delta == 0:
                    continue
                key = (d["file"], d["page"], d["chunk"] + delta)
                if key in pos2i:
                    want.add(pos2i[key])

        selected = [docs[int(i)] for i in sorted(want)]
        context = "\n\n".join(
            [f"Source: {d['file']} (page {d['page']}, chunk {d['chunk']})\n{d['text']}"
            for d in selected]
        )
        return context, selected

    def retrieve_context_fallback(
        self,
        question: str,
        docs: list[dict],
        doc_embs: np.ndarray,
        allowed_files: set[str],
        k_primary: int = 6,
        k_fallback: int = 16,
    ):
        """
        1er intento: k pequeño + vecinos
        Si el contexto es pobre, 2do intento: k más grande + más vecinos
        SIN keywords.
        """
        ctx1, src1 = self.retrieve_context_with_neighbors(
            question, docs, doc_embs, k=k_primary, allowed_files=allowed_files, neighbor_radius=1
        )

        # Heurística genérica de "contexto pobre": muy corto o muy repetitivo
        too_short = len(ctx1) < 1200
        if not too_short:
            return ctx1, src1

        ctx2, src2 = self.retrieve_context_with_neighbors(
            question, docs, doc_embs, k=k_fallback, allowed_files=allowed_files, neighbor_radius=2
        )
        return ctx2, src2

        
    @staticmethod
    def infer_files_from_question(question: str, all_pdfs: list[str]) -> list[str]:
        def _norm(s: str) -> str:
            s = s.lower()
            s = re.sub(r"[^a-z0-9]+", " ", s)
            return re.sub(r"\s+", " ", s).strip()

        qn = _norm(question)
        if not qn:
            return []

        scored = []
        for p in all_pdfs:
            base = _norm(os.path.basename(p).replace(".pdf", ""))
            tokens = [t for t in base.split() if len(t) >= 3]

            score = 0
            for t in tokens:
                if t in qn:
                    score += 1

            # bonus si menciona algo tipo C02 / C01
            q_code = re.search(r"\bc\d{1,3}\b", qn)
            b_code = re.search(r"\bc\d{1,3}\b", base)
            if q_code and b_code and q_code.group(0) in base:
                score += 3

            if score > 0:
                scored.append((score, p))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [p for _, p in scored[:3]]    