import re
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timezone

from domain.task import Task 

class PlanManager:
    """
    Manages the migration plan stored in a Markdown file.
    Responsibilities:
    - Parsing the plan.md file into a list of Task objects.
    - Finding the next actionable task.
    - Updating the status of tasks and rewriting the plan.md file.
    """
    def __init__(self, plan_file_path: Path):
        self.plan_file_path: Path = plan_file_path
        self.tasks: List[Task] = []
        self.task_map: Dict[str, Task] = {} 
        self._load_and_parse_plan()

    def _load_and_parse_plan(self):
        """Loads the plan from the file and parses it."""
        print(f"PlanManager: Loading plan from {self.plan_file_path}")
        if not self.plan_file_path.exists():
            print(f"PlanManager: Plan file not found at {self.plan_file_path}. No tasks loaded.")
            self.tasks = []
            self.task_map = {}
            return

        try:
            with open(self.plan_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._parse_plan_markdown(content)
            print(f"PlanManager: Loaded {len(self.tasks)} tasks.")
        except Exception as e:
            print(f"PlanManager: Error loading or parsing plan file: {e}")
            self.tasks = []
            self.task_map = {}
            
    def _parse_plan_markdown(self, markdown_content: str):
        """
        Parses the Markdown content into a list of Task objects.
        Expected format:
        - [ ] task-id-001 <!-- status: todo; notes: Some notes -->
          - description: A clear description of the task.
          - depends: [optional-dependency-task-id-1, optional-dependency-task-id-2]
        """
        self.tasks = []
        self.task_map = {}
        current_task_lines = []
        
        
        
        task_line_regexes = [
            re.compile(r"^\s*-\s*\[([x\s])\]\s*\*\*(T[0-9]+):.*?\*\*\s*(<!--.*-->)?"),  
            re.compile(r"^\s*-\s*\[([x\s])\]\s*\*\*([a-zA-Z0-9_-]+):.*?\*\*\s*(<!--.*-->)?"),  
            re.compile(r"^\s*-\s*\[([x\s])\]\s*(T[0-9]+):.*?\s*(<!--.*-->)?"),          
            re.compile(r"^\s*-\s*\[([x\s])\]\s*([a-zA-Z0-9_-]+):.*?\s*(<!--.*-->)?"),   
            re.compile(r"^\s*-\s*\[([x\s])\]\s*(T[0-9]+)\s*-\s*.*?\s*(<!--.*-->)?"),    
            re.compile(r"^\s*-\s*\[([x\s])\]\s*([a-zA-Z0-9_-]+)\s*-\s*.*?\s*(<!--.*-->)?"), 
            re.compile(r"^\s*-\s*\[([x\s])\]\s*(T[0-9]+)\s+.*?\s*(<!--.*-->)?"),        
            re.compile(r"^\s*-\s*\[([x\s])\]\s*([a-zA-Z0-9_-]+)\s+.*?\s*(<!--.*-->)?"), 
            re.compile(r"^\s*-\s*\[([x\s])\]\s*([a-zA-Z0-9_-]+)\s*(<!--.*-->)?"),       
        ]
        

        
        desc_re = re.compile(r"^\s*-\s*description:\s*(.*)")
        depends_re = re.compile(r"^\s*-\s*depends:\s*\[(.*)\]")

        current_task_data = {}

        lines = markdown_content.splitlines()
        
        def process_previous_task():
            if current_task_data.get("id"):
                task = Task(
                    id=current_task_data["id"],
                    description=current_task_data.get("description", "No description provided."),
                    status=current_task_data.get("status", "todo"),
                    depends_on=current_task_data.get("depends_on", []),
                    notes=current_task_data.get("notes")
                )
                task.raw_lines = current_task_data.get("raw_lines", [])
                self.tasks.append(task)
                self.task_map[task.id] = task
            current_task_data.clear()

        for i, line in enumerate(lines):
            match_task_line = None
            for r in task_line_regexes:
                m = r.match(line)
                if m:
                    match_task_line = m
                    break
            if match_task_line:
                process_previous_task() 

                status_char = match_task_line.group(1)
                task_id = match_task_line.group(2)
                metadata_comment = None
                
                if len(match_task_line.groups()) >= 3:
                    metadata_comment = match_task_line.group(3)
                elif len(match_task_line.groups()) >= 4:
                    metadata_comment = match_task_line.group(4)

                status = "todo"
                if status_char == 'x': status = "done"
                

                current_task_data["id"] = task_id
                current_task_data["status"] = status
                current_task_data["raw_lines"] = [line]
                current_task_data["depends_on"] = [] 

                
                if metadata_comment:
                    notes_match = re.search(r"notes:\s*(.*?)\s*;", metadata_comment)
                    if notes_match:
                        current_task_data["notes"] = notes_match.group(1).strip()
                    

            elif current_task_data.get("id"): 
                current_task_data["raw_lines"].append(line)
                match_desc = desc_re.match(line)
                if match_desc:
                    current_task_data["description"] = match_desc.group(1).strip()
                    continue

                match_depends = depends_re.match(line)
                if match_depends:
                    deps_str = match_depends.group(1).strip()
                    if deps_str:
                        current_task_data["depends_on"] = [d.strip() for d in deps_str.split(',') if d.strip()]
                    continue
            else: 
                
                
                pass
        
        process_previous_task() 

    def _serialize_plan_markdown(self) -> str:
        """Converts the list of Task objects back into Markdown format, preserving original non-task lines if possible."""
        
        
        
        
        output_lines = ["# Migration Plan\n"] 
        
        for task in self.tasks:
            status_char = ' '
            if task.status == "done": status_char = 'x'
            

            metadata_parts = [] 
            if task.status == "done": 
                metadata_parts.append(f"status: {task.status}")
                if task.notes:
                    metadata_parts.append(f"notes: {task.notes}")
                metadata_parts.append(f"updated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
            
            metadata_comment = f" <!-- {'; '.join(metadata_parts)}; -->" if metadata_parts else ""

            output_lines.append(f"- [{status_char}] {task.id}{metadata_comment}")
            output_lines.append(f"  - description: {task.description}")
            if task.depends_on:
                output_lines.append(f"  - depends: [{', '.join(task.depends_on)}]")
            output_lines.append("") 

        return "\n".join(output_lines)

    def get_next_task(self) -> Optional[Task]:
        """
        Finds the next task that is 'todo' and whose dependencies are met ('done').
        Returns None if no such task exists.
        """
        for task in self.tasks:
            if task.status == "todo":
                dependencies_met = True
                if task.depends_on:
                    for dep_id in task.depends_on:
                        dep_task = self.task_map.get(dep_id)
                        if not dep_task or dep_task.status != "done":
                            dependencies_met = False
                            break
                if dependencies_met:
                    print(f"PlanManager: Next task found: {task.id}")
                    return task
        print("PlanManager: No actionable 'todo' tasks with met dependencies found.")
        return None

    def update_task_status(self, task_id: str, new_status: str, notes: Optional[str] = None):
        """
        Updates the status and notes of a specific task to 'done' and rewrites the plan file.
        If new_status is not 'done', the update is ignored.
        """
        task = self.task_map.get(task_id)
        if not task:
            print(f"PlanManager: Error - Task with ID '{task_id}' not found for update.")
            return

        if new_status != "done":
            print(f"PlanManager: Task '{task_id}' update ignored. Only 'done' status is accepted for updates. Received: '{new_status}'.")
            return

        print(f"PlanManager: Updating task '{task_id}' to status 'done'")
        task.status = "done" 
        if notes: 
            task.notes = notes
        
        
        try:
            updated_markdown = self._serialize_plan_markdown()
            with open(self.plan_file_path, 'w', encoding='utf-8') as f:
                f.write(updated_markdown)
            print(f"PlanManager: Plan file {self.plan_file_path} updated.")
        except Exception as e:
            print(f"PlanManager: Error writing updated plan file: {e}")

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        return self.task_map.get(task_id)

    def reload_plan(self):
        """Forces a reload and re-parse of the plan file."""
        self._load_and_parse_plan()

if __name__ == '__main__':
    
    print("PlanManager direct execution (for testing).")
    dummy_project_root = Path(__file__).resolve().parent.parent
    dummy_sandbox_dir = dummy_project_root / "sandbox_plan_manager_test"
    dummy_sandbox_dir.mkdir(exist_ok=True)
    dummy_plan_file = dummy_sandbox_dir / "test_plan.md"

    initial_plan_content = """
# Migration Plan

- [ ] T01 <!-- status: todo; -->
  - description: Initialize React workspace
  - depends: []

- [ ] T02 <!-- status: todo; -->
  - description: Copy static assets
  - depends: [T01]

- [ ] T03
  - description: Setup basic routing
  - depends: [T01]
  
- [x] T00-SETUP <!-- status: done; notes: Initial setup complete; updated: 2025-05-08T18:00:00Z; -->
  - description: Initial project setup tasks
"""
    with open(dummy_plan_file, 'w', encoding='utf-8') as f:
        f.write(initial_plan_content)

    pm = PlanManager(dummy_plan_file)
    print(f"Initial tasks loaded: {len(pm.tasks)}")
    for t in pm.tasks:
        print(f"  - {t}")

    next_task = pm.get_next_task()
    if next_task: 
        print(f"\nFirst next task: {next_task.id} - {next_task.description}")
        pm.update_task_status(next_task.id, "done", "Workspace initialized successfully.")
    else:
        
        
        t00 = pm.get_task_by_id("T00-SETUP")
        if t00 and t00.status != "done":
            print("Manually setting T00-SETUP to done for test flow.")
            pm.update_task_status("T00-SETUP", "done", "Manually set for test.")
            next_task = pm.get_next_task() 
            if next_task:
                 print(f"\nFirst next task (after T00 fix): {next_task.id} - {next_task.description}")
                 pm.update_task_status(next_task.id, "done", "Workspace initialized successfully.")

    next_task = pm.get_next_task() 
    if next_task:
        print(f"\nSecond next task: {next_task.id} - {next_task.description}")
        pm.update_task_status(next_task.id, "failed", "Failed to copy assets due to permission error.")

    next_task = pm.get_next_task() 
    if next_task:
        print(f"\nThird next task: {next_task.id} - {next_task.description}")
        
        pm.update_task_status(next_task.id, "done", "Routing setup.")
        
    print("\nFinal plan content in memory:")
    for t in pm.tasks:
        print(f"  - ID: {t.id}, Status: {t.status}, Notes: {t.notes}")

    print(f"\nCheck the content of {dummy_plan_file}")
