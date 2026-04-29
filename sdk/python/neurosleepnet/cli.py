import argparse
import json
import os
import sys
import webbrowser
import httpx
from typing import Optional

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

    config = {
        "project_name": name,
        "project_id": project_id,
        "api_key": "local_test_key",
        "initialized_at": httpx.get("https://worldtimeapi.org/api/timezone/Etc/UTC").json()["datetime"] if check_connectivity() else "N/A"
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

def open_dashboard():
    """Opens the project dashboard in the browser."""
    config = get_project_config()
    project_id = config.get("project_id", "default")
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
    subparsers.add_parser("dashboard", help="Open the local dashboard")

    # stack
    stack_parser = subparsers.add_parser("stack", help="Manage the local docker stack")
    stack_parser.add_argument("action", choices=["up", "down", "reset"], help="Action to perform")

    args = parser.parse_args()

    if args.command == "init":
        init_project(args.name)
    elif args.command == "status":
        show_status()
    elif args.command == "dashboard":
        open_dashboard()
    elif args.command == "stack":
        manage_stack(args.action)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
