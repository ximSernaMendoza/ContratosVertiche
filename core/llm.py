import os
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    provider = os.getenv("LLM_PROVIDER", "OLLAMA").upper()

    if provider == "OLLAMA":
        from langchain_ollama import ChatOllama
        model = os.getenv("OLLAMA_MODEL", "llama3:8b")
        return ChatOllama(model=model, temperature=0.1)

    if provider == "OPENAI":
        from langchain_openai import ChatOpenAI
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=0.1)

    raise ValueError(f"LLM_PROVIDER no soportado: {provider}")
