import argparse
import sys
import logging

from .suite import BenchmarkSuite

def main():
    parser = argparse.ArgumentParser(description="NeuroSleepNet Benchmark Runner")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument("--model", type=str, default="mock-model", help="Model to benchmark against")
    parser.add_argument("--scenario", "--scenarios", type=str, default="all", help="Specific scenario(s) to run, or 'all'")
    parser.add_argument("--api-key", type=str, default="demo_key", help="NeuroSleepNet API Key")
    parser.add_argument("--export-html", type=str, help="Path to export HTML report")
    parser.add_argument("--export-json", "--output", type=str, help="Path to export JSON report")
    parser.add_argument("--publish", action="store_true", help="Publish results to backend")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.command == "run":
        suite = BenchmarkSuite(api_key=args.api_key, model=args.model)
        
        scenarios = ["all"] if args.scenario == "all" else [args.scenario]
        reporter = suite.run(scenarios=scenarios)
        
        reporter.print_report()
        
        if args.export_html:
            reporter.export_html(args.export_html)
            
        if args.export_json:
            reporter.export_json(args.export_json)
            
        if args.publish:
            suite.push_to_backend(reporter)

if __name__ == "__main__":
    main()
