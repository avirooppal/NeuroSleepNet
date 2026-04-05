import httpx
from typing import Any, Dict, List, Optional


class NeuroSleepClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8001/api/v1",
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-KEY": self.api_key,
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
            return response.json()

    # Tasks
    def create_task(self, name: str) -> Dict[str, Any]:
        return self._request("POST", "/tasks/", json={"name": name})

    def list_tasks(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/tasks/")

    # Memories
    def add_memory(self, content: str, task_id: Optional[str] = None, metadata: Dict[str, Any] = {}) -> Dict[str, Any]:
        payload = {"content": content, "metadata": metadata}
        if task_id:
            payload["task_id"] = task_id
        return self._request("POST", "/memories/", json=payload)

    def list_memories(self, task_id: Optional[str] = None, page: int = 1, size: int = 50) -> List[Dict[str, Any]]:
        params = {"page": page, "size": size}
        if task_id:
            params["task_id"] = task_id
        return self._request("GET", "/memories/", params=params)

    # Search
    def search(self, query: str, task_id: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
        payload = {"query": query, "top_k": top_k}
        if task_id:
            payload["task_id"] = task_id
        return self._request("POST", "/search/", json=payload)

    # Sleep
    def trigger_sleep(self) -> Dict[str, Any]:
        return self._request("POST", "/sleep/trigger")

    def get_sleep_history(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/sleep/history")

    # Dashboard
    def get_stats(self) -> Dict[str, Any]:
        return self._request("GET", "/dashboard/stats")
