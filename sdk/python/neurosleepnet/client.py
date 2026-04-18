import httpx
from typing import Any, Dict, List, Optional
import os

class NeuroSleepClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8001/api",
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Internal helper for sync requests.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(headers=self.headers, timeout=self.timeout) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Allow empty responses or plain text
            try:
                return response.json()
            except Exception:
                return {"text": response.text}

    def ping(self) -> Dict[str, Any]:
        """Validates the API key and connection."""
        return self._request("GET", "/v1/ping")

    # Memories V2
    def store_memory(self, content: str, project: str, tags: list = [], importance: float = 1.0, session_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {"content": content, "project": project, "tags": tags, "importance": importance}
        if session_id:
            payload["session_id"] = session_id
        return self._request("POST", "/v1/memories", json=payload)

    def retrieve(self, query: str, project: str, top_k: int = 5) -> List[Dict[str, Any]]:
        params = {"query": query, "project": project, "top_k": top_k}
        res = self._request("GET", "/v1/memories/retrieve", params=params)
        return res.get("memories", [])

    def forget(self, memory_id: Optional[str] = None, query: Optional[str] = None, older_than_days: Optional[int] = None) -> Dict[str, Any]:
        if memory_id:
            return self._request("DELETE", f"/v1/memories/{memory_id}")
        elif query:
            return self._request("POST", "/v1/memories/forget-query", json={"query": query})
        return {}

    def explain_last(self, project: str) -> Dict[str, Any]:
        return self._request("GET", "/v1/memories/explain_last", params={"project": project})

    # Projects
    def list_projects(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/v1/projects")

    def create_project(self, name: str) -> Dict[str, Any]:
        return self._request("POST", "/v1/projects", json={"name": name})

    def trigger_sleep(self, project: str) -> Dict[str, Any]:
        return self._request("POST", "/v1/sleep/trigger", json={"project": project})
