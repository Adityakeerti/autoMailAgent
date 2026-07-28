import json
import logging
import httpx
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("llm_service")

class MultiFallbackLLM:
    """
    Multi-fallback LLM service supporting Groq (Llama 3.3 70B, DeepSeek R1 70B), Ollama Cloud API (OLLAMA_API_KEY),
    Official Llama API (LLAMA_API_KEY), GitHub GPT-4o, and Gemini.
    """

    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.llama_key = settings.LLAMA_API_KEY
        self.ollama_key = settings.OLLAMA_API_KEY
        self.ollama_base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.gemini_key = settings.GEMINI_API_KEY
        self.github_token = settings.GITHUB_TOKEN

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, high_tier: bool = False, json_mode: bool = False) -> str:
        """
        Main entry point for generating completion with automatic provider fallback.
        Prioritizes Ollama Cloud/Host, Groq Llama 3.3 70B, DeepSeek R1 70B, Llama API, and GitHub GPT-4o.
        """
        if high_tier:
            # High-capability tier for resume extraction:
            # 1. Ollama Cloud API / Hosted (OLLAMA_API_KEY / OLLAMA_BASE_URL)
            # 2. Llama 3.3 70B (Groq)
            # 3. DeepSeek R1 70B (Groq)
            # 4. Llama API (LLAMA_API_KEY)
            # 5. GitHub GPT-4o
            # 6. Gemini 2.0 Flash / Gemini Pro
            # 7. Local Ollama
            providers = ["ollama_cloud", "groq_llama_70b", "groq_deepseek_70b", "llama_api", "github_gpt4o", "gemini_pro", "ollama_local"]
        else:
            # Med-high tier for email personalization & hooks:
            providers = ["ollama_cloud", "groq_llama_70b", "groq_deepseek_70b", "llama_api", "groq_8b", "github_gpt4o_mini", "gemini_flash", "ollama_local"]

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

        if json_mode:
            return "{}"
        raise RuntimeError(f"All LLM fallback providers failed. Last error: {last_error}")

    async def expand_role_keywords(self, role: str) -> List[str]:

        """
        Fast keyword expansion layer to make role searching keyword-agnostic.
        Maps roles (e.g. 'Software Engineer') to synonyms & acronyms (SDE, SWE, Software Developer, Fullstack, etc.).
        """
        if not role or not role.strip():
            return []

        role_clean = role.strip()
        role_lower = role_clean.lower()

        # Static fast map for common tech roles (0ms resolution)
        STATIC_ROLE_MAP = {
            "software engineer": ["software engineer", "sde", "swe", "software developer", "full stack engineer", "backend developer", "programmer"],
            "sde": ["sde", "software development engineer", "software engineer", "swe", "software developer"],
            "software developer": ["software developer", "software engineer", "sde", "swe", "application developer", "programmer"],
            "ai ml engineer": ["ai ml engineer", "ai developer", "ml engineer", "machine learning engineer", "ai engineer", "data scientist", "deep learning engineer"],
            "ai engineer": ["ai engineer", "ai developer", "ml engineer", "machine learning engineer", "ai ml engineer", "artificial intelligence engineer"],
            "ml engineer": ["ml engineer", "machine learning engineer", "ai engineer", "ai developer", "data scientist"],
            "frontend developer": ["frontend developer", "frontend engineer", "react developer", "ui engineer", "web developer", "frontend dev"],
            "backend developer": ["backend developer", "backend engineer", "python developer", "node developer", "java engineer", "backend dev"],
            "full stack engineer": ["full stack engineer", "full stack developer", "fullstack engineer", "software engineer", "web developer"],
            "data engineer": ["data engineer", "big data engineer", "data pipeline engineer", "etl developer", "analytics engineer"],
            "devops engineer": ["devops engineer", "site reliability engineer", "sre", "cloud engineer", "infrastructure engineer"],
        }

        keywords = [role_clean]

        # Check static map
        if role_lower in STATIC_ROLE_MAP:
            for k in STATIC_ROLE_MAP[role_lower]:
                if k.lower() not in [kw.lower() for kw in keywords]:
                    keywords.append(k)

        # Call fast LLM for dynamic expansion
        try:
            prompt = f"Given the job title '{role_clean}', return a JSON object with key 'keywords' containing 6-8 synonymous job titles, acronyms, and variations used in tech recruitment. Output JSON format only: {{\"keywords\": [\"...\"]}}"
            res = await self.generate_text(prompt, high_tier=False, json_mode=True)
            if res:
                data = json.loads(res)
                expanded = data.get("keywords", [])
                for item in expanded:
                    if item and isinstance(item, str) and item.strip():
                        val = item.strip()
                        if val.lower() not in [kw.lower() for kw in keywords]:
                            keywords.append(val)
        except Exception as e:
            logger.debug(f"LLM keyword expansion fallback for '{role_clean}': {e}")

        return keywords

    async def _call_provider(self, provider: str, prompt: str, system_prompt: Optional[str], json_mode: bool) -> str:
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:

            # --- OLLAMA CLOUD / HOSTED / REMOTE ---
            if provider == "ollama_cloud":
                if not self.ollama_key:
                    raise ValueError("OLLAMA_API_KEY not set")

                base_url = self.ollama_base_url
                url = f"{base_url}/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.ollama_key}",
                    "Content-Type": "application/json"
                }
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload: Dict[str, Any] = {
                    "model": "llama3.3",
                    "messages": messages,
                    "temperature": 0.2
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                
                # Try native Ollama chat API format on base URL
                alt_url = f"{base_url}/api/chat"
                alt_resp = await client.post(alt_url, headers=headers, json={
                    "model": "llama3.3",
                    "messages": messages,
                    "stream": False
                })
                if alt_resp.status_code == 200:
                    return alt_resp.json().get("message", {}).get("content", "")

                raise ValueError(f"Ollama Cloud error {resp.status_code}: {resp.text}")


            # --- GROQ HOSTED MODELS (Llama 3.3 70B & DeepSeek R1 70B) ---
            elif provider.startswith("groq"):
                if not self.groq_key:
                    raise ValueError("GROQ_API_KEY not set")

                if provider == "groq_deepseek_70b":
                    model = "deepseek-r1-distill-llama-70b"
                elif provider == "groq_llama_70b":
                    model = "llama-3.3-70b-versatile"
                else:
                    model = "llama-3.1-8b-instant"

                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload: Dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.2}
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    if "<think>" in content and "</think>" in content:
                        content = content.split("</think>")[-1].strip()
                    return content
                raise ValueError(f"Groq ({model}) error {resp.status_code}: {resp.text}")

            # --- OFFICIAL LLAMA API HOSTED ---
            elif provider == "llama_api":
                if not self.llama_key:
                    raise ValueError("LLAMA_API_KEY not set")
                url = "https://api.llama-api.com/chat/completions"
                headers = {"Authorization": f"Bearer {self.llama_key}", "Content-Type": "application/json"}
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload = {"model": "llama3.3-70b", "messages": messages, "temperature": 0.2}
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                raise ValueError(f"Llama API error {resp.status_code}: {resp.text}")

            # --- GITHUB MODELS (GPT-4o) ---
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

            # --- GEMINI MODELS ---
            elif provider.startswith("gemini"):
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

            # --- OLLAMA LOCAL ---
            elif provider == "ollama_local":
                base_url = self.ollama_base_url
                url = f"{base_url}/api/generate"
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                payload = {"model": "llama3", "prompt": full_prompt, "stream": False}
                if json_mode:
                    payload["format"] = "json"
                headers = {"Content-Type": "application/json"}
                if self.ollama_key:
                    headers["Authorization"] = f"Bearer {self.ollama_key}"
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
                raise ValueError(f"Ollama local error {resp.status_code}: {resp.text}")

        raise ValueError(f"Unknown provider {provider}")

llm_service = MultiFallbackLLM()
