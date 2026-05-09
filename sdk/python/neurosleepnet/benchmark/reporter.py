import json
from typing import Dict, Any, List
from datetime import datetime

class ReportGenerator:
    def __init__(self, run_id: str, model: str, results: List[Dict[str, Any]], reproduce_cmd: str = ""):
        self.run_id = run_id
        self.model = model
        self.results = results
        self.date = datetime.now()
        self.reproduce_cmd = reproduce_cmd
        
        # Calculate overall score
        valid_scores = [r["score"] for r in self.results if "score" in r]
        self.overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

    def print_report(self):
        """Prints a rich terminal report."""
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            
        print("+" + "="*62 + "+")
        print(f"|  NeuroSleepNet Benchmark Report{' '*30}|")
        print(f"|  Model: {self.model[:20]:<20} | Date: {self.date.strftime('%Y-%m-%d'):<15} |")
        print("+" + "="*62 + "+")
        
        for res in self.results:
            name = res.get("scenario", "Unknown")
            score = res.get("score", 0.0)
            
            # Simple progress bar visualization
            bar_len = int(score / 100 * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            
            # Formatting improvement indicator
            raw = res.get('raw_score', 0)
            nsn = res.get('nsn_score', 0)
            if raw == 0 and nsn > 0:
                delta_str = f"{score:3.0f}% ✓"
            elif raw > 0 and nsn > raw:
                delta_str = f"+{int(nsn-raw):2d}% ✓"
            else:
                delta_str = f"{score:3.0f}% ✓"
            
            print(f"|  {name:<26} {bar}  {delta_str:<6} |")
        
        print("+" + "="*62 + "+")
        print(f"|  Overall Memory Score:  {int(self.overall_score)}/100 \U0001f9e0{' '*26}|")
        print(f"|  Run ID: {self.run_id:<46} |")
        print("+" + "="*62 + "+")
        
        if self.reproduce_cmd:
            print("\n  Reproduce this run:")
            print(f"  $ {self.reproduce_cmd}\n")

    def export_json(self, path: str):
        """Exports the results to JSON."""
        data = {
            "run_id": self.run_id,
            "model": self.model,
            "date": self.date.isoformat(),
            "overall_score": self.overall_score,
            "results": self.results
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Exported JSON report to {path}")

    def export_html(self, path: str):
        """Generates a standalone HTML report file."""
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Inter', system-ui, sans-serif; background: #0a0a0f; color: #fff; padding: 2rem; }}
  .container {{ max-width: 800px; margin: 0 auto; background: #1a1a24; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); border: 1px solid #333; }}
  h1 {{ color: #00e5cc; }}
  .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #333; padding-bottom: 1rem; margin-bottom: 2rem; }}
  .row {{ display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid #222; }}
  .bar-bg {{ background: #333; width: 200px; height: 12px; border-radius: 6px; overflow: hidden; }}
  .bar-fill {{ background: #00e5cc; height: 100%; }}
  .score {{ font-weight: bold; width: 80px; text-align: right; }}
  .overall {{ font-size: 1.5rem; margin-top: 2rem; padding-top: 1rem; border-top: 2px solid #333; text-align: center; color: #ffb347; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>NeuroSleepNet Benchmark</h1>
        <div>Model: <strong>{self.model}</strong></div>
      </div>
      <div style="text-align: right; color: #888;">
        <div>Date: {self.date.strftime('%Y-%m-%d')}</div>
        <div>ID: {self.run_id}</div>
      </div>
    </div>
"""
        for res in self.results:
            score = res.get("score", 0.0)
            raw_score = res.get("raw_score", 0.0)
            ctrl_score = res.get("control_score", raw_score)
            name = res.get("scenario", "Unknown")
            improvement = score - raw_score
            html += f"""
    <div class="row">
      <div style="width: 200px;">{name}</div>
      <div style="flex: 1;">
        <div style="font-size:0.7rem; color:#888; margin-bottom:2px;">Active</div>
        <div class="bar-bg"><div class="bar-fill" style="width: {score}%;"></div></div>
        <div style="font-size:0.7rem; color:#888; margin-top:4px;">Control (disabled)</div>
        <div class="bar-bg"><div class="bar-fill" style="width: {ctrl_score}%; background:#888;"></div></div>
        <div style="font-size:0.7rem; color:#888; margin-top:4px;">Baseline (no NSN)</div>
        <div class="bar-bg"><div class="bar-fill" style="width: {raw_score}%; background:#444;"></div></div>
      </div>
      <div class="score">+{improvement:.0f}%</div>
    </div>
"""
        
        reproduce_section = ""
        if self.reproduce_cmd:
            reproduce_section = f"""
    <div style="margin-top:2rem; padding:1rem; background:#111; border-radius:8px; border:1px solid #333;">
      <div style="color:#888; font-size:0.75rem; margin-bottom:0.5rem;">REPRODUCE THIS RUN</div>
      <code style="color:#00e5cc; font-family: monospace;">$ {self.reproduce_cmd}</code>
    </div>"""
        
        html += f"""
    <div class="overall">
      Overall Memory Score: {int(self.overall_score)}/100 &#x1F9E0;
    </div>
    {reproduce_section}
  </div>
</body>
</html>"""
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Exported HTML report to {path}")
