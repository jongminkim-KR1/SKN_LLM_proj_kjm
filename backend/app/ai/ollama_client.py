"""
Ollama LLM 클라이언트
"""
import requests
from typing import Optional


class OllamaClient:
    def __init__(self, model: str = "EEVE-Korean-10.8B:latest", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.chat_url = f"{base_url}/api/chat"

        server_type = "RunPod GPU" if "runpod" in base_url.lower() else "로컬"
        print(f"{'🚀' if 'runpod' in base_url.lower() else '💻'} {server_type} Ollama 서버 사용: {base_url}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 500
            }
        }

        try:
            response = requests.post(self.chat_url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get('message', {}).get('content', '').strip()
        except requests.exceptions.RequestException as e:
            print(f"Ollama API 오류: {e}")
            return "[AI 응답 실패]"
