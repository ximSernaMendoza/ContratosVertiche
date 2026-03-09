from __future__ import annotations
import streamlit as st
from agents.legal import run_legal_agent
from core.pdf_service import PdfService
from core.rag_service import RagService



class LegalService:
    def __init__(self, pdf_service: PdfService, rag_service: RagService) -> None:
        self.pdf_service = pdf_service
        self.rag_service = rag_service

    def answer_legal_question(self, question: str, contrato_pdf: str, codigo_federal_pdf: str, codigo_estatal_pdf: str, docs: list[dict], doc_embs):
        contract_full_text = self.pdf_service.extract_full_pdf_text(contrato_pdf)
        if not contract_full_text.strip():
                    st.error("No se pudo extraer el texto completo del contrato seleccionado.")
                    st.stop()
                    
        federal_context, federal_sources = self.rag_service.retrieve_context_fallback(
            question, docs, doc_embs, allowed_files={codigo_federal_pdf}, k_primary=6, k_fallback=12
        )
        state_context, state_sources = self.rag_service.retrieve_context_fallback(
            question, docs, doc_embs, allowed_files={codigo_estatal_pdf}, k_primary=6, k_fallback=12
        )
        answer = run_legal_agent(
            question=question,
            contract_full_text=contract_full_text,
            federal_context=federal_context,
            state_context=state_context,
            legal_sources={
                "codigo_federal": codigo_federal_pdf,
                "codigo_estatal": codigo_estatal_pdf,
                "contrato": contrato_pdf,
            },
        )
        sources = [{"file": contrato_pdf, "page": "COMPLETO"}] + federal_sources + state_sources
        return answer, sources
