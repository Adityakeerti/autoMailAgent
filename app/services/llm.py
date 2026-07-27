import json
import logging
import httpx
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("llm_service")

class MultiFallbackLLM:
    """
    Multi-fallback LLM service handling requests across Gemini, Groq, GitHub Models, and Ollama.
    Supports high/big model tier (for extraction) and med-high model tier (for personalization, hook lines, etc).
    """

    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        self.github_token = settings.GITHUB_TOKEN
        self.ollama_key = settings.OLLAMA_API_KEY

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, high_tier: bool = False, json_mode: bool = False) -> str:
        """
        Main entry point for generating completion with automatic provider fallback.
        :param prompt: User prompt
        :param system_prompt: System prompt
        :param high_tier: True for big/high-capability models (e.g. resume extraction), False for med/high models (personalization, hooks)
        :param json_mode: Request structured JSON output
        """
        # Define provider call order based on tier
        if high_tier:
            providers = ["gemini_pro", "github_gpt4o", "groq_70b", "gemini_flash", "ollama"]
        else:
            providers = ["groq_8b", "groq_70b", "gemini_flash", "github_gpt4o_mini", "ollama"]

        last_error = None
        for provider in providers:
            try:
                logger.info(f"Attempting LLM completion using provider: {provider}")
                res = await self._call_provider(provider, prompt, system_prompt, json_mode)
                if res and res.strip():
                    return res.strip()
            except Exception as e:
                logger.warning(f"LLM Provider {provider} failed: {e}. Falling back to next provider.")
                last_error = e

        # If all API calls fail or no keys are configured, provide structured fallback response
        if json_mode:
            return "{}"
        raise RuntimeError(f"All LLM fallback providers failed. Last error: {last_error}")

    async def _call_provider(self, provider: str, prompt: str, system_prompt: Optional[str], json_mode: bool) -> str:
        async with httpx.AsyncClient(timeout=45.0) as client:
            if provider.startswith("gemini"):
                if not self.gemini_key:
                    raise ValueError("GEMINI_API_KEY not set")
                model = "gemini-2.0-flash-exp" if "flash" in provider else "gemini-1.5-flash-latest"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                payload = {
                    "contents": [{"parts": [{"text": full_prompt}]}]
                }
                if json_mode:
                    payload["generationConfig"] = {"responseMimeType": "application/json"}

                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                raise ValueError(f"Gemini error {resp.status_code}: {resp.text}")

            elif provider.startswith("groq"):
                if not self.groq_key:
                    raise ValueError("GROQ_API_KEY not set")
                model = "llama-3.3-70b-versatile" if "70b" in provider else "llama-3.1-8b-instant"
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload: Dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.3}
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                raise ValueError(f"Groq error {resp.status_code}: {resp.text}")

            elif provider.startswith("github"):
                if not self.github_token:
                    raise ValueError("GITHUB_TOKEN not set")
                model = "gpt-4o" if "gpt4o" in provider and "mini" not in provider else "gpt-4o-mini"
                url = "https://models.inference.ai.azure.com/chat/completions"
                headers = {"Authorization": f"Bearer {self.github_token}", "Content-Type": "application/json"}
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload = {"model": model, "messages": messages, "temperature": 0.3}
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                raise ValueError(f"GitHub Models error {resp.status_code}: {resp.text}")

            elif provider == "ollama":
                url = "http://localhost:11434/api/generate"
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                payload = {"model": "llama3", "prompt": full_prompt, "stream": False}
                if json_mode:
                    payload["format"] = "json"
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
                raise ValueError(f"Ollama error {resp.status_code}: {resp.text}")

        raise ValueError(f"Unknown provider {provider}")

llm_service = MultiFallbackLLM()
