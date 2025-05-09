import os
from pathlib import Path
import pathspec

def load_project_context(project_dir: Path) -> str:
    """
    Loads all relevant files from the project_dir into a single string,
    respecting .gitignore rules and a predefined set of common ignored
    directories and files.

    Args:
        project_dir: The root directory of the project to load.

    Returns:
        A string containing the concatenated content of all relevant files,
        or an empty string if no files are loaded or the directory is invalid.
    """
    print(f"ContextLoader: Loading project context from: {project_dir}")
    if not project_dir.exists() or not project_dir.is_dir():
        print(f"ContextLoader: Error - Directory {project_dir} not found or is not a directory.")
        return ""

    context_parts = []

    
    always_ignored_basenames_dirs = {".git", "node_modules", "__pycache__", ".angular", ".vscode", ".idea", "dist", "coverage"}
    always_ignored_basenames_files = {".DS_Store"}

    
    gitignore_file = project_dir / ".gitignore"
    gitignore_patterns = []
    if gitignore_file.is_file():
        with open(gitignore_file, 'r', encoding='utf-8') as f:
            gitignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    
    
    spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, gitignore_patterns)

    for root_str, dirs, files in os.walk(project_dir, topdown=True):
        current_root_path = Path(root_str)

        
        dirs[:] = [d_name for d_name in dirs if d_name not in always_ignored_basenames_dirs]

        
        
        
        original_dirs_copy = list(dirs) 
        dirs[:] = [] 
        for d_name in original_dirs_copy:
            dir_path_relative_to_project_dir = (current_root_path / d_name).relative_to(project_dir)
            
            if not spec.match_file(str(dir_path_relative_to_project_dir) + '/'):
                dirs.append(d_name)
            else:
                print(f"  ContextLoader: Skipping directory (matched in .gitignore): {dir_path_relative_to_project_dir}")
        
        for file_name in files:
            if file_name in always_ignored_basenames_files:
                print(f"  ContextLoader: Skipping file (always ignored basename): {current_root_path / file_name}")
                continue

            file_abs_path = current_root_path / file_name
            file_path_relative_to_project_dir = file_abs_path.relative_to(project_dir)

            
            if spec.match_file(str(file_path_relative_to_project_dir)):
                print(f"  ContextLoader: Skipping file (matched in .gitignore): {file_path_relative_to_project_dir}")
                continue
            
            
            if file_name == ".gitignore" and current_root_path == project_dir:
                print(f"  ContextLoader: Skipping .gitignore file itself from context content.")
                continue

            try:
                with open(file_abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                context_parts.append(f"--- File: {file_path_relative_to_project_dir.as_posix()} ---\n{content}\n--- End File: {file_path_relative_to_project_dir.as_posix()} ---")
                print(f"  ContextLoader: Loaded: {file_path_relative_to_project_dir.as_posix()}")
            except Exception as e:
                print(f"  ContextLoader: Error loading {file_path_relative_to_project_dir.as_posix()}: {e}")
    
    if not context_parts:
        print("ContextLoader: No files loaded into context after filtering.")
        return ""
        
    print(f"ContextLoader: Total files loaded into context: {len(context_parts)}")
    return "\n\n".join(context_parts)
