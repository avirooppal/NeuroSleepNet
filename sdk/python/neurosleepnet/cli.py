import argparse
import json
import os
import sys
import webbrowser
import httpx
from typing import Optional
from .dashboard import serve_dashboard_cli

# Base URL for local backend
BACKEND_URL = os.environ.get("NSN_BACKEND_URL", "http://localhost:8000/api/v1")
DASHBOARD_URL = os.environ.get("NSN_DASHBOARD_URL", "http://localhost:8080")

def get_project_config():
    """Reads local project config if exists."""
    if os.path.exists(".nsn.json"):
        with open(".nsn.json", "r") as f:
            return json.load(f)
    return {}

def save_project_config(config):
    """Saves local project config."""
    with open(".nsn.json", "w") as f:
        json.dump(config, f, indent=2)

def check_connectivity():
    """Checks if the backend is reachable."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False

def init_project(name: Optional[str]):
    """Initializes a new project."""
    if not name:
        name = os.path.basename(os.getcwd())

    print(f"[*] Initializing NeuroSleepNet project: {name}...")

    if not check_connectivity():
        print("[!] Warning: Local backend (http://localhost:8000) is not reachable.")
        print("    Make sure to run 'docker compose up' to start the services.")
    
    # Try to create/get project from backend
    try:
        # Note: We use a default local key for now
        headers = {"Authorization": "Bearer local_test_key"}
        response = httpx.post(
            f"{BACKEND_URL}/projects/",
            json={"name": name},
            headers=headers,
            timeout=5.0
        )
        if response.status_code in (200, 201):
            project_data = response.json()
            project_id = project_data.get("id")
            print(f"[+] Project registered with ID: {project_id}")
        else:
            print(f"[!] Backend returned status {response.status_code}. Using name as fallback ID.")
            project_id = name
    except Exception as e:
        print(f"[!] Could not register project with backend: {e}")
        project_id = name

    # P2-7: Use stdlib datetime — avoids external HTTP call to worldtimeapi.org
    # which breaks in air-gapped environments and is a privacy concern.
    from datetime import datetime, timezone as _tz
    initialized_at = datetime.now(_tz.utc).isoformat()

    config = {
        "project_name": name,
        "project_id": project_id,
        "api_key": "local_test_key",
        "initialized_at": initialized_at,
    }
    save_project_config(config)

    print("\n" + "="*60)
    print("  NeuroSleepNet Initialized Successfully!  ")
    print("="*60)
    print(f"  Project ID:   {project_id}")
    print(f"  Dashboard:    {DASHBOARD_URL}/dashboard/{project_id}")
    print("="*60)
    print("\nNext steps:")
    print(f"  1. Ensure backend is running: nsn stack up")
    print(f"  2. In your code, use: nsn.init(project='{project_id}')")
    print("\nHappy coding!\n")

def show_status():
    """Shows current project status."""
    config = get_project_config()
    if not config:
        print("[!] No NeuroSleepNet project found in this directory. Run 'nsn init' first.")
        return

    print(f"NeuroSleepNet Project Status")
    print("-" * 30)
    print(f"Name:       {config.get('project_name')}")
    print(f"ID:         {config.get('project_id')}")
    print(f"Backend:    {BACKEND_URL}")
    
    is_up = check_connectivity()
    print(f"Status:     {'ONLINE' if is_up else 'OFFLINE (Backend unreachable)'}")

def open_dashboard(local: bool = True, project: Optional[str] = None, data_dir: Optional[str] = None, port: int = 3000):
    """Opens or serves the project dashboard."""
    config = get_project_config()
    project_id = project or config.get("project_id", "default")
    
    # Auto-detect data_dir
    if not data_dir:
        data_dir = config.get("data_dir")
    
    if not data_dir:
        if os.path.exists("./demo_data"):
            data_dir = "./demo_data"
        else:
            data_dir = "~/.neurosleepnet"
    
    if local:
        data_dir = os.path.expanduser(data_dir)
        db_path = os.path.join(data_dir, "neurosleepnet.db")
        serve_dashboard_cli(db_path=db_path, project=project_id, port=port)
    else:
        url = f"{DASHBOARD_URL}/dashboard/{project_id}"
        print(f"[*] Opening dashboard: {url}")
        webbrowser.open(url)

# Bundled docker-compose template for PyPI users
COMPOSE_TEMPLATE = """
services:
  api:
    image: neurosleepnet/api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://nsn:nsn@db:5432/neurosleepnet
      - REDIS_URL=redis://redis:6379/0
      - EMBED_SERVICE_URL=http://nsn-embed:8001
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: neurosleepnet
      POSTGRES_USER: nsn
      POSTGRES_PASSWORD: nsn
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nsn -d neurosleepnet"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine

  nsn-embed:
    image: neurosleepnet/embed:latest
    environment:
      - MODEL=BAAI/bge-small-en-v1.5

  frontend:
    image: neurosleepnet/frontend:latest
    environment:
      - VITE_API_URL=http://localhost:8080/api/v1
    depends_on:
      - api

  nginx:
    image: neurosleepnet/gateway:latest
    ports:
      - "8080:80"
    depends_on:
      - api
      - frontend
"""

def manage_memories(action: str, query: Optional[str] = None, project: Optional[str] = None, data_dir: Optional[str] = None, user_id: Optional[str] = None):
    """CLI helper to manage memories."""
    config = get_project_config()
    project_id = project or config.get("project_id", "default")
    if not data_dir:
        data_dir = config.get("data_dir") or ("./demo_data" if os.path.exists("./demo_data") else "~/.neurosleepnet")
    
    from .local_store import LocalStore
    store = LocalStore(data_dir=data_dir)
    
    if action == "list":
        mems = store.list_memories(project_id, limit=20)
        print(f"\n--- Recent Memories ({project_id}) ---")
        for m in mems:
            print(f"[{m['memory_type'].upper()}] {m['content'][:80]}...")
    elif action == "search" and query:
        mems = store.search_text(query, project_id, limit=5)
        print(f"\n--- Search Results for '{query}' ---")
        for m in mems:
            # P2-3: search_text returns attention_score, not score
            score = m.get("attention_score", m.get("score", 0.0))
            print(f"[{m['memory_type'].upper()}] (Score: {score:.2f}) {m['content'][:80]}...")
    elif action == "forget":
        if user_id:
            count = store.forget_user(user_id, project_id)
            print(f"[+] Forgotten {count} memories for user '{user_id}'.")
        else:
            count = store.forget_project(project_id)
            print(f"[+] Cleared {count} memories for project '{project_id}'.")

def trigger_sleep_cli(project: Optional[str] = None, data_dir: Optional[str] = None):
    """Manually trigger a sleep cycle from CLI."""
    config = get_project_config()
    project_id = project or config.get("project_id", "default")
    if not data_dir:
        data_dir = config.get("data_dir") or ("./demo_data" if os.path.exists("./demo_data") else "~/.neurosleepnet")
    
    from .local_store import LocalStore
    store = LocalStore(data_dir=data_dir)
    print(f"[*] Running sleep consolidation for {project_id}...")
    stats = store.run_consolidation(project_id)
    print(f"[+] Done! Boosted={stats['boosted']}, Deduped={stats['deduped']}, Promoted={stats['promoted']}")

def show_stats_cli(project: Optional[str] = None, data_dir: Optional[str] = None):
    """Show quick stats in terminal."""
    config = get_project_config()
    project_id = project or config.get("project_id", "default")
    if not data_dir:
        data_dir = config.get("data_dir") or ("./demo_data" if os.path.exists("./demo_data") else "~/.neurosleepnet")
    
    from .local_store import LocalStore
    store = LocalStore(data_dir=data_dir)
    s = store.get_stats(project_id)
    print(f"\nNeuroSleepNet Stats: {project_id}")
    print("-" * 40)
    print(f"Total Memories:    {s['total_memories']}")
    print(f"Health Score:      {s['health_score']:.2f}")
    print(f"Pinned Rules:      {s['pinned']}")
    print(f"Recall Misses:     {s['miss_count']}")
    print(f"Sleep Cycles:      {s['sleep_cycles_run']}")
    print("-" * 40 + "\n")

def manage_stack(action: str):
    """Manages the docker-compose stack."""
    compose_file = "docker-compose.yml" if os.path.exists("docker-compose.yml") else "nsn-compose.yml"
    
    if action == "up":
        print("[*] Starting NeuroSleepNet local stack...")
        if not os.path.exists(compose_file) and compose_file == "nsn-compose.yml":
            with open(compose_file, "w") as f:
                f.write(COMPOSE_TEMPLATE.strip())
        os.system(f"docker compose -f {compose_file} up -d")
        print("[+] Stack is up! Visit http://localhost:8080 to see the dashboard.")
        
    elif action == "down":
        print("[*] Stopping NeuroSleepNet local stack...")
        os.system(f"docker compose -f {compose_file} down")
        print("[+] Stack stopped.")
        
    elif action == "reset":
        print("[!] PERFORMING FULL SYSTEM RESET...")
        # Stop and remove volumes
        os.system(f"docker compose -f {compose_file} down -v")
        # Clear local SDK cache
        db_path = os.path.expanduser("~/.neurosleepnet/neurosleepnet.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            print("[+] Local SDK cache cleared.")
        # Restart
        manage_stack("up")

def main():
    parser = argparse.ArgumentParser(description="NeuroSleepNet CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("name", nargs="?", help="Project name (defaults to folder name)")

    # status
    subparsers.add_parser("status", help="Show current project status")

    # dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Open or serve the dashboard")
    dash_parser.add_argument("--remote", action="store_true", help="Open the remote cloud dashboard instead of local")
    dash_parser.add_argument("--project", help="Project ID to show (local mode)")
    dash_parser.add_argument("--data-dir", help="Data directory (local mode)")
    dash_parser.add_argument("--port", type=int, default=3000, help="Port to run on (local mode)")

    # stack
    stack_parser = subparsers.add_parser("stack", help="Manage the local docker stack")
    stack_parser.add_argument("action", choices=["up", "down", "reset"], help="Action to perform")

    # memories
    mem_parser = subparsers.add_parser("memories", help="List or search memories")
    mem_parser.add_argument("action", choices=["list", "search", "forget"], default="list")
    mem_parser.add_argument("query", nargs="?", help="Search query")
    mem_parser.add_argument("--project", help="Project ID")
    mem_parser.add_argument("--user", help="User ID (for forget action)")

    # sleep
    sleep_parser = subparsers.add_parser("sleep", help="Trigger manual sleep consolidation")
    sleep_parser.add_argument("--project", help="Project ID")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show project statistics")
    stats_parser.add_argument("--project", help="Project ID")

    args = parser.parse_args()

    if args.command == "init":
        init_project(args.name)
    elif args.command == "status":
        show_status()
    elif args.command == "dashboard":
        open_dashboard(local=not args.remote, project=args.project, data_dir=args.data_dir, port=args.port)
    elif args.command == "stack":
        manage_stack(args.action)
    elif args.command == "memories":
        manage_memories(args.action, args.query, args.project, user_id=args.user)
    elif args.command == "sleep":
        trigger_sleep_cli(args.project)
    elif args.command == "stats":
        show_stats_cli(args.project)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
