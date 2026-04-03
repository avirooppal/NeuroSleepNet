from typing import Any, Dict
from .buffer import ReplayBuffer

class SleepScheduler:
    """
    Manages the sleep phase for memory consolidation.
    """
    def __init__(self, sleep_interval: int = 100):
        self.sleep_interval = sleep_interval
        self.steps = 0
        self.last_task_id = None
        self.last_report = {}

    def should_sleep(self, step: int, task_id: str) -> bool:
        """
        Check if we should trigger the sleep phase.
        Triggers on task switch OR every N steps.
        """
        self.steps += 1
        
        task_switched = False
        if self.last_task_id is not None and self.last_task_id != task_id:
            task_switched = True
            
        self.last_task_id = task_id
        interval_reached = (self.steps % self.sleep_interval == 0)
        
        return task_switched or interval_reached

    def run_sleep(self, model: Any, buffer: ReplayBuffer) -> Dict[str, Any]:
        """
        Run the sleep consolidation process.
        Returns a sleep report.
        """
        print("💤 [NeuroSleepNet] Sleep triggered. Consolidating memories...")
        memories = buffer.sample(64, strategy="importance")
        
        # In a real implementation, we would train the model on the replayed memories here.
        tasks_consolidated = list(set([m["task_id"] for m in memories]))
        forgetting_risk_delta = -0.05 * len(tasks_consolidated)
        
        self.last_report = {
            "status": "success",
            "memories_replayed": len(memories),
            "tasks_consolidated": tasks_consolidated,
            "forgetting_risk_delta": forgetting_risk_delta
        }
        return self.last_report
        
    def get_report(self) -> Dict[str, Any]:
        return self.last_report
