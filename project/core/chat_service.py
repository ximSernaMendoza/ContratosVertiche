from __future__ import annotations

from openai import OpenAI
from config.settings import SETTINGS

class ChatService:
    def __init__(self) -> None:
        self.client = SETTINGS.get_openai_client()

    @staticmethod
    def _history_to_messages(history: list[dict], max_turns: int = 30) -> list[dict]:
        recent = history[-max_turns:] if len(history) > max_turns else history
        messages = []

        for m in recent:
            role = m.get("role", "")
            text = (m.get("text", "") or "").strip()

            if not text:
                continue

            if role == "user":
                messages.append({"role": "user", "content": text})
            elif role in ("bot", "assistant"):
                messages.append({"role": "assistant", "content": text})

        return messages


    def ask_llm_chat(
        self,
        question: str,
        context: str,
        history: list[dict],
        max_turns: int = 30,
    ) -> str:
        """
        Respuesta de chat usando GPT-4o-mini.
        Si hay contexto RAG, lo usa.
        Si no hay contexto, responde como chat general del asistente.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente especializado en análisis de contratos. "
                    "Responde en español. "
                    "Usa prioritariamente el contexto recuperado del RAG cuando exista. "
                    "Si el usuario pide un dato específico y no aparece en el contexto, responde exactamente: "
                    "'No especificado en contrato'. "
                    "No inventes cláusulas, montos, fechas ni obligaciones. "
                    "Sé claro, profesional y estructurado."
                ),
            }
        ]

        messages.extend(self._history_to_messages(history, max_turns=max_turns))

        user_prompt = (
            f"CONTEXTO RAG:\n{context if context else 'Sin contexto recuperado.'}\n\n"
            f"PREGUNTA DEL USUARIO:\n{question}"
        )

        messages.append({"role": "user", "content": user_prompt})

        resp = self.client.chat.completions.create(
            model=SETTINGS.CHAT_MODEL,
            messages=messages,
            temperature=0.2,
        )

        return (resp.choices[0].message.content or "").strip()