from __future__ import annotations

from openai import OpenAI
from config.settings import SETTINGS


class ChatService:
    def __init__(self) -> None:
        self.client = OpenAI(base_url=SETTINGS.LMSTUDIO_BASE, api_key=SETTINGS.LMSTUDIO_API_KEY)

    def ask_llm_chat(self, question: str, context: str, history: list[dict], max_turns: int = 30) -> str:
        """
        history: lista de dicts {"role": "user"|"bot", "text": "..."} guardada en session_state
        max_turns: cuántos mensajes previos (pares user/bot) usar como memoria corta
        """

        # tomar solo los últimos mensajes (memoria corta)
        recent = history[-max_turns:] if len(history) > max_turns else history

        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente especializado en análisis de contratos.\n"
                    "Responde usando el CONTEXTO recuperado del RAG. Si falta información, di 'No especificado en contrato'.\n"
                    "Sé claro, con bullets si ayuda."
                ),
            }
        ]

        # historial (sin contexto viejo)
        for m in recent:
            r = m.get("role", "")
            if r == "user":
                messages.append({"role": "user", "content": m.get("text", "")})
            elif r == "bot":
                messages.append({"role": "assistant", "content": m.get("text", "")})

        # mensaje actual con contexto
        messages.append({
            "role": "user",
            "content": f"CONTEXTO (RAG):\n{context}\n\nPREGUNTA:\n{question}"
        })

        resp = self.client.chat.completions.create(
            model=SETTINGS.CHAT_MODEL,
            messages=messages,
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()