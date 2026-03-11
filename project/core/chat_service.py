from __future__ import annotations

from openai import OpenAI
from config.settings import SETTINGS

class ChatService:
    def __init__(self) -> None:
        self.model = SETTINGS.configure_gemini()

    @staticmethod
    def _history_to_text(history: list[dict], max_turns: int = 30) -> str:
        recent = history[-max_turns:] if len(history) > max_turns else history
        lines = []

        for m in recent:
            role = m.get("role", "")
            text = (m.get("text", "") or "").strip()

            if not text:
                continue

            if role == "user":
                lines.append(f"Usuario: {text}")
            elif role in ("bot", "assistant"):
                lines.append(f"Asistente: {text}")

        return "\n".join(lines)


    def ask_llm_chat(
        self,
        question: str,
        context: str,
        history: list[dict],
        max_turns: int = 30,
    ) -> str:
        """
        Respuesta de chat usando Gemini.
        Si hay contexto RAG, lo usa.
        Si no hay contexto, responde como chat general del asistente.
        """
        history_text = self._history_to_text(history, max_turns=max_turns)

        prompt = f"""
Eres un asistente especializado en análisis de contratos.

Reglas:
- Responde en español.
- Usa prioritariamente el CONTEXTO recuperado del RAG si está disponible.
- Si el dato solicitado no aparece en el contexto/documento, responde exactamente: "No especificado en contrato".
- No inventes cláusulas, montos, fechas ni obligaciones.
- Sé claro, estructurado y profesional.
- Usa viñetas cuando ayude.

HISTORIAL RECIENTE:
{history_text if history_text else "Sin historial previo."}

CONTEXTO RAG:
{context if context else "Sin contexto recuperado."}

PREGUNTA DEL USUARIO:
{question}
""".strip()

        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1200,
            },
        )

        text = getattr(response, "text", None)
        if text and text.strip():
            return text.strip()

        # fallback por si Gemini devuelve partes/candidates
        try:
            parts = response.candidates[0].content.parts
            return "".join(
                getattr(part, "text", "") for part in parts if getattr(part, "text", "")
            ).strip()
        except Exception:
            return "No fue posible generar una respuesta en este momento."