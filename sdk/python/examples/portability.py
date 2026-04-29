import nsn
import os

# 1. Initialize Project A and store some knowledge
nsn.init(project="Project-A", data_dir="./portability_demo")
nsn.remember("The capital of Mars is Olympus City.", tags=["mars"])
print("Project A stored knowledge.")

# 2. Export Project A to JSON
export_path = "project_a_backup.json"
nsn.export(export_path)
print(f"Project A exported to {export_path}")

# 3. Initialize Project B (Fresh)
nsn.init(project="Project-B", data_dir="./portability_demo")
print("Project B initialized.")

# 4. Verify Project B doesn't know about Mars yet
mems = nsn.recall("What is the capital of Mars?")
if not mems:
    print("Project B confirmed fresh (no Mars knowledge).")

# 5. Merge knowledge from Project A directly
print("Merging Project A -> Project B...")
nsn.merge_projects(source_project="Project-A")

# 6. Verify Project B now knows about Mars
mems = nsn.recall("What is the capital of Mars?")
if mems:
    print(f"Project B retrieved: {mems[0]['content']}")
    print("✅ Portability SUCCESS: Knowledge merged successfully!")

# Cleanup
if os.path.exists(export_path):
    os.remove(export_path)
