import os
from openai import OpenAI

def get_client() -> OpenAI:
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()

    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GROQ_API_KEY.")
        return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY.")
    return OpenAI(api_key=api_key)

def chat_text(model: str, messages: list[dict], temperature: float = 0.2) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""
