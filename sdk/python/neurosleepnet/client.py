import httpx
from typing import Any, Dict, List

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
        with httpx.Client(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Allow empty responses or plain text
            try:
                return response.json()
            except Exception:
                return {"text": response.text}

    def ping(self) -> Dict[str, Any]:
        """Validates the API key and connection."""
        return self._request("GET", "/v1/ping/")

    # Memories
    def store_memory(self, **kwargs) -> Dict[str, Any]:
        payload = {
            "content": kwargs.get("content"), 
            "project_id": kwargs.get("project_id") or kwargs.get("project"), 
            "tags": kwargs.get("tags") or [], 
            "importance": kwargs.get("importance", 1.0),
            "session_id": kwargs.get("session_id"),
            "ttl_days": kwargs.get("ttl_days")
        }
        return self._request("POST", "/v1/memories/", json=payload)

    def retrieve(self, **kwargs) -> List[Dict[str, Any]]:
        params = {
            "query": kwargs.get("query"), 
            "project_id": kwargs.get("project_id") or kwargs.get("project"), 
            "top_k": kwargs.get("top_k", 5)
        }
        res = self._request("GET", "/v1/memories/retrieve", params=params)
        return res.get("memories", [])

    def import_memories(self, **kwargs) -> Dict[str, Any]:
        items = kwargs.get("items", [])
        return self._request("POST", "/v1/memories/batch", json=items)

    def forget(self, **kwargs) -> Dict[str, Any]:
        memory_id = kwargs.get("memory_id")
        query = kwargs.get("query")
        older_than_days = kwargs.get("older_than_days")
        if memory_id:
            return self._request("DELETE", f"/v1/memories/{memory_id}")
        elif query:
            return self._request("POST", "/v1/memories/forget-query", json={"query": query, "older_than_days": older_than_days})
        return {}

    def trigger_sleep(self, **kwargs) -> Dict[str, Any]:
        project = kwargs.get("project_id") or kwargs.get("project")
        return self._request("POST", "/v1/sleep/trigger", json={"project_id": project})

    def sleep_status(self, **kwargs) -> Dict[str, Any]:
        return self._request("GET", "/v1/sleep/status")

    def get_stats(self, **kwargs) -> Dict[str, Any]:
        project = kwargs.get("project_id") or kwargs.get("project")
        return self._request("GET", "/v1/analytics/stats", params={"project_id": project})

    def explain_last(self, **kwargs) -> Dict[str, Any]:
        project = kwargs.get("project_id") or kwargs.get("project")
        return self._request("GET", "/v1/memories/explain_last", params={"project_id": project})

    def feedback(self, **kwargs) -> Dict[str, Any]:
        memory_id = kwargs.get("memory_id")
        helpful = kwargs.get("helpful", True)
        return self._request("POST", "/v1/memories/feedback", json={"memory_id": memory_id, "helpful": helpful})

    def pin(self, **kwargs) -> Dict[str, Any]:
        memory_id = kwargs.get("memory_id")
        return self._request("POST", f"/v1/memories/{memory_id}/pin")

    def unpin(self, **kwargs) -> Dict[str, Any]:
        memory_id = kwargs.get("memory_id")
        return self._request("POST", f"/v1/memories/{memory_id}/unpin")
