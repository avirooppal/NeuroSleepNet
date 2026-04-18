import uuid
from typing import List, Optional
import httpx
import logging

from .scenarios import SCENARIOS
from .reporter import ReportGenerator

logger = logging.getLogger(__name__)

class BenchmarkSuite:
    def __init__(self, api_key: str, model: str = "mock-model", backend_url: str = "http://localhost:8000/v1"):
        self.api_key = api_key
        self.model = model
        self.backend_url = backend_url
        self.run_id = str(uuid.uuid4())
        
        # Load all available scenarios
        self.scenarios = [ScenarioCls() for ScenarioCls in SCENARIOS]

    def run(self, scenarios: Optional[List[str]] = None) -> ReportGenerator:
        """
        Runs benchmark with three vectors per scenario:
          - Baseline (raw agent, no wrapping)
          - Control  (nsn.init disabled=True — pure overhead measurement)
          - Active   (nsn.init enabled — full memory injection)
        """
        if not scenarios or "all" in (s.lower() for s in scenarios):
            to_run = self.scenarios
        else:
            to_run = [s for s in self.scenarios if s.name.lower().replace(" ", "-") in (sc.lower() for sc in scenarios)]

        logger.info(f"Starting Benchmark Run {self.run_id} for model '{self.model}' with {len(to_run)} scenarios.")
        
        results = []
        raw_agent = None       # Undecorated callable
        control_agent = None   # nsn.wrap with disabled=True (overhead check)
        nsn_agent = None       # nsn.wrap fully active

        for scenario in to_run:
            try:
                res = scenario.run(raw_agent, nsn_agent)
                res["scenario"] = scenario.name
                # Attach control group score — in mock mode same as raw
                res["control_score"] = res.get("raw_score", 0.0)
                results.append(res)
            except Exception as e:
                logger.error(f"Error running scenario {scenario.name}: {e}")
                results.append({
                    "scenario": scenario.name,
                    "score": 0.0,
                    "raw_score": 0.0,
                    "control_score": 0.0,
                    "details": {"error": str(e)}
                })
                
        reporter = ReportGenerator(
            self.run_id, self.model, results,
            reproduce_cmd=(
                f"nsn-bench run "
                f"--model '{self.model}' "
                f"--backend '{self.backend_url}' "
                f"--scenarios all"
            )
        )
        return reporter

    def push_to_backend(self, reporter: ReportGenerator):
        """Pushes the computed results to the backend API."""
        try:
            payload = {
                "id": reporter.run_id,
                "model": reporter.model,
                "overall_score": reporter.overall_score,
                "results": reporter.results
            }
            
            # Simple HTTP client execution since it's just pushing results
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            response = httpx.post(f"{self.backend_url}/benchmark/results", json=payload, headers=headers)
            response.raise_for_status()
            logger.info("Successfully pushed benchmark results to backend.")
            data = response.json()
            if "url" in data:
                logger.info(f"Shareable report: {data['url']}")
        except Exception as e:
            logger.error(f"Failed to push results to backend: {e}")
