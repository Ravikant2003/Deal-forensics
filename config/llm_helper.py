"""
LLM Provider Helper: Switch between Groq and Ollama
"""

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel

from config.settings import (
    LLM_PROVIDER,
    GROQ_API_KEY,
    AGENT_MODEL,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
)


def get_llm(temperature: float = 0) -> BaseChatModel:
    """
    Get the configured LLM based on LLM_PROVIDER setting.
    
    Returns:
        ChatGroq or ChatOllama instance
    """
    if LLM_PROVIDER == "ollama":
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=temperature,
        )
    else:
        return ChatGroq(
            model=AGENT_MODEL,
            temperature=temperature,
            api_key=GROQ_API_KEY,
        )