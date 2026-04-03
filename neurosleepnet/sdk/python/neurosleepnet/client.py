import requests
from typing import List, Dict, Optional

class NeuroSleepClient:
    def __init__(self, api_key: str = "nsk_local", base_url: str = "http://localhost:8000/api"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def write(self, user_id: str, session_id: str, messages: List[Dict[str, str]], task_id: str = "default"):
        resp = requests.post(
            f"{self.base_url}/v2/write",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "messages": messages,
                "task_id": task_id
            },
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        resp.raise_for_status()
        return resp.json()

    def read(self, user_id: str, query: str, task_id: str = "default") -> Dict[str, str]:
        resp = requests.post(
            f"{self.base_url}/v2/read",
            json={
                "user_id": user_id,
                "query": query,
                "task_id": task_id
            },
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        resp.raise_for_status()
        return resp.json()
