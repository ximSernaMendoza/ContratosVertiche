from __future__ import annotations

import os
import streamlit as st
from config.settings import SETTINGS


class ConsultaSection:
    def __init__(self, session, storage, pdf_service, rag_service, chat_service, legal_service, finance_service, components) -> None:
        self.session = session
        self.storage = storage
        self.pdf_service = pdf_service
        self.rag_service = rag_service
        self.chat_service = chat_service
        self.legal_service = legal_service
        self.finance_service = finance_service
        self.components = components

    def render(self) -> None:
        from agents.router import run_orchestrator, list_agents

        self.session.normalize_messages()
        self.components.render_chat_messages(self.session.messages, self.finance_service)
        agents = list_agents()
        mode = st.radio("Modo de consulta", options=["General", "Por agente"], index=0, horizontal=True)
        selected_agent_key = None
        if mode == "Por agente":
            selected_agent_key = st.selectbox("Selecciona un agente", options=list(agents.keys()), format_func=lambda k: agents[k]["label"])
            st.info(agents[selected_agent_key]["description"])

        #PDFs Disponibles
        all_pdfs = self.storage.list_all_pdfs()
        if not all_pdfs:
            st.warning("No se encontraron PDFs en el bucket.")
            st.stop()

        selected_pdf = None
        selected_legal_docs = []

        # Selección de documentos
        if mode == "Por agente" and selected_agent_key == "legal":
            st.markdown("#### Consulta legal especializada")

            # 1) Código Civil Federal (siempre activo)
            codigo_federal_pdf = self.pdf_service.find_codigo_civil_federal(all_pdfs)
            st.text_input("Código Civil Federal (siempre activo)", value=codigo_federal_pdf or "", disabled=True)

            # 2) Código Civil Estatal (lo eliges tú)
            codigos_estatales = self.pdf_service.find_codigos_civiles_estatales(all_pdfs)
            codigo_estatal_pdf = st.selectbox("Selecciona el Código Civil del Estado", options=codigos_estatales, index=0)

            # 3) Contrato (lo eliges tú)
            contratos = [p for p in all_pdfs if "contrato" in os.path.basename(p).lower()]  
            contrato_pdf = st.selectbox("Selecciona el contrato a analizar", options=contratos, index=0)
           
            # Documentos finales del agente legal
            selected_legal_docs = self.pdf_service.unique_preserve_order([codigo_federal_pdf, codigo_estatal_pdf, contrato_pdf])
            st.caption("Fuentes legales activas:")
            for doc in selected_legal_docs:
                st.write(f"- {doc}")
        else:
            selected_pdf = st.selectbox("Documento a consultar", options=all_pdfs, index=0)
            st.caption(f"Consultando SOLO: {selected_pdf}")

        #Botones prompts
        cols = st.columns(4)
        for (label, prompt), col in zip(SETTINGS.chip_prompts.items(), cols):
            with col:
                if st.button(label, key=f"chip_{label}", use_container_width=True):
                    st.session_state.question_draft = prompt
                    self.session.set_auto_submit(prompt)
                    st.rerun()

        # Input + Enviar
        if self.session.consume_clear_question_flag():
            st.session_state.question_draft = ""

        question = st.text_input("Pregunta", placeholder="Pregunta lo que quieras...", label_visibility="collapsed", key="question_draft")
        ask = st.button("Enviar", use_container_width=False)
        
        #Ejecutar consulta
        submitted = self.session.get_auto_submit() or (question.strip() if ask and question.strip() else None)
        if not submitted:
            return

        user_question = submitted.strip()
        self.session.append_user_message(user_question)
        chart_data = None
        
        # Determinar archivos a consultar
        if mode == "Por agente" and selected_agent_key == "legal":
            files_for_query = tuple(selected_legal_docs)
            allowed_files = set(selected_legal_docs)
        else:
            files_for_query = (selected_pdf,)
            allowed_files = {selected_pdf}
        docs, doc_embs = self.rag_service.build_index(SETTINGS.max_pages, SETTINGS.chunk_chars, SETTINGS.overlap, files_for_query)
        
        # Flujo especial del agente legal        
        if mode == "Por agente" and selected_agent_key == "legal":
            final_answer, sources = self.legal_service.answer_legal_question(user_question, selected_legal_docs[2], selected_legal_docs[0], selected_legal_docs[1], docs, doc_embs)
        else:
            context, sources = self.rag_service.retrieve_context_fallback(user_question, docs, doc_embs, allowed_files, SETTINGS.top_k, 16)
            if mode == "General":
                final_answer = self.chat_service.ask_llm_chat(user_question, context, self.session.messages, max_turns=12)
            else:
                results = run_orchestrator(user_question, context, agent_key=selected_agent_key)
                final_answer = "\n\n".join([f"{k}: {v}" for k, v in results.items()])
                if selected_agent_key == "finanzas":
                    chart_data = self.finance_service.build_chart_data(context)
        self.session.append_bot_message(final_answer, sources=sources, chart_data=chart_data)
        self.session.set_auto_submit(None)
        self.session.clear_question_input_on_next_render()
        st.rerun()
