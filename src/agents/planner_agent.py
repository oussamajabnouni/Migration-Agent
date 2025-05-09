import os
import re
from pathlib import Path
from google import genai
from dotenv import load_dotenv
import traceback
from rich.console import Console

console = Console()


project_root_for_dotenv = Path(__file__).resolve().parent.parent.parent
dotenv_path = project_root_for_dotenv / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    
else:
    
    load_dotenv()
    

class PlannerAgent:
    """
    The PlannerAgent is responsible for generating a migration plan
    from an Angular project context to a React project using Google Gemini.
    """
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-pro-preview-05-06"): 
        """
        Initializes the PlannerAgent.

        Args:
            api_key: Optional Google API key. If None, attempts to use GEMINI_API_KEY from env.
            model_name: The Gemini model to use.
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name
        self.client = None

        if self.api_key:
            try:
                
                self.client = genai.Client(api_key=self.api_key)
                console.print(f"🤖 [bold blue]PlannerAgent: Google GenAI client initialized using google-genai SDK for model [cyan]{self.model_name}[/].[/]")
            except Exception as e:
                console.print(f"❌ [bold red]PlannerAgent: Error initializing Google GenAI client with google-genai SDK:[/] [red]{e}[/]")
                self.client = None 
        else:
            console.print("⚠️ [bold yellow]PlannerAgent: GEMINI_API_KEY not found. LLM features will be disabled. Using fallback plan.[/]")

    def _get_gitignore_patterns(self, project_path: Path) -> list[str]:
        """Reads .gitignore from the project path and returns a list of patterns."""
        gitignore_file = project_path / ".gitignore"
        patterns = []
        if gitignore_file.exists():
            with open(gitignore_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        
                        
                        
                        patterns.append(line)
        return patterns

    def _is_ignored(self, file_path: Path, project_root: Path, gitignore_patterns: list[str]) -> bool:
        """Checks if a file path should be ignored based on .gitignore patterns."""
        relative_path_str = str(file_path.relative_to(project_root))
        for pattern in gitignore_patterns:
            
            if pattern.endswith('/'): 
                if relative_path_str.startswith(pattern.rstrip('/')):
                    return True
            elif pattern.startswith('*'):
                if file_path.name.endswith(pattern[1:]):
                    return True
            elif pattern == file_path.name: 
                return True
            elif relative_path_str == pattern: 
                return True
            
        return False

    def _build_project_context(self, input_dir: Path) -> str:
        """
        Builds a string containing the content of all relevant files in the Angular project,
        respecting .gitignore.
        """
        console.print(f"📂 [bold blue]PlannerAgent: Building project context from[/] [italic magenta]{input_dir}[/]...")
        context_parts = []
        gitignore_patterns = self._get_gitignore_patterns(input_dir)
        

        
        
        always_ignore_dirs = ['.git', 'node_modules', 'dist', 'coverage', '.angular', '.vscode', '.idea']
        always_ignore_files = ['.DS_Store']

        for item in input_dir.rglob("*"):
            
            if any(ignored_dir in item.parts for ignored_dir in always_ignore_dirs):
                
                if item.is_dir(): 
                    
                    
                    pass 
                continue

            if item.is_file():
                if item.name in always_ignore_files:
                    
                    continue

                if self._is_ignored(item, input_dir, gitignore_patterns):
                    
                    continue

                try:
                    relative_path = item.relative_to(input_dir)
                    
                    content = item.read_text(encoding="utf-8", errors="ignore")
                    context_parts.append(f"--- File: {str(relative_path).replace(os.sep, '/')} ---\n{content}\n--- End File: {str(relative_path).replace(os.sep, '/')} ---")
                except Exception as e:
                    context_parts.append(f"--- File: {str(item.relative_to(input_dir)).replace(os.sep, '/')} ---\nError reading file: {e}\n--- End File: {str(item.relative_to(input_dir)).replace(os.sep, '/')} ---")
        
        if not context_parts:
            console.print("⚠️ [bold yellow]PlannerAgent: No files found or included after .gitignore filtering.[/]")
            return "No relevant project files found to build context."
            
        full_context = "\n\n".join(context_parts)
        
        return full_context

    def _generate_fallback_plan(self, output_dir: Path, input_dir: Path) -> str:
        """Generates a hardcoded fallback plan."""
        return f"""
# Migration Plan (Fallback)

- [ ] T01
  - description: Review existing Angular project structure and dependencies in {input_dir}. Note that the React target is already scaffolded with Vite and TypeScript in {output_dir}.
- [ ] T02
  - description: Identify core Angular modules, components, services, and routing configurations.
- [ ] T03
  - description: Plan the equivalent React component hierarchy and state management strategy (e.g., Context API, Zustand, Redux).
- [ ] T04
  - description: Copy static assets (images, fonts, etc.) from {input_dir}/src/assets (or equivalent) to {output_dir}/public or {output_dir}/src/assets.
- [ ] T05
  - description: Set up basic React Router (if not already part of the Vite template) in {output_dir}/src/App.tsx or main application file.
- [ ] T06
  - description: Convert Angular's main AppModule and AppComponent to React's root component (e.g., App.tsx).
- [ ] T07
  - description: Incrementally convert Angular components to React functional components. Start with simpler, shared components.
- [ ] T08
  - description: Convert Angular services to React custom hooks or utility functions.
- [ ] T09
  - description: Implement routing based on Angular's route definitions.
- [ ] T10
  - description: Address styling (CSS, SCSS, CSS-in-JS) for converted components.
- [ ] T11
  - description: Test converted components and integrated parts of the application.
- [ ] T12
  - description: Refactor and optimize the React codebase.
"""

    def generate_plan(self, angular_project_context: str, output_dir: Path, input_dir: Path) -> str:
        """
        Generates a migration plan based on the provided Angular project context.
        If angular_project_context is empty, it will be built from input_dir.

        Args:
            angular_project_context: A string containing the full content of the Angular project.
                                     If empty, it will be built from input_dir.
            output_dir: The target directory for the React project.
            input_dir: The source directory of the Angular project.

        Returns:
            A string in Markdown format representing the migration plan.
        """
        console.print("📝 [bold blue]PlannerAgent: Generating migration plan...[/]")

        if not angular_project_context and input_dir:
            console.print(f"ℹ️ [bold blue]PlannerAgent: angular_project_context is empty, building from[/] [italic magenta]{input_dir}[/]")
            angular_project_context = self._build_project_context(input_dir)
            if angular_project_context == "No relevant project files found to build context.":
                 console.print("❌ [bold red]PlannerAgent: Error - Could not build Angular project context from input_dir.[/]")
                 return f"# Migration Plan Error\n\n{angular_project_context}"
        elif not angular_project_context and not input_dir:
            console.print("❌ [bold red]PlannerAgent: Error - Angular project context is empty and input_dir not provided.[/]")
            return "# Migration Plan Error\n\nAngular project context and input_dir were not provided."

        if not self.client:
            console.print("⚠️ [bold yellow]PlannerAgent: LLM client not available. Using fallback plan.[/]")
            return self._generate_fallback_plan(output_dir, input_dir)

        prompt = rf"""
You are an expert Angular to React migration assistant.
The user wants to migrate an Angular project to React.
The target React project has ALREADY BEEN SCAFFOLDED using Vite and TypeScript in the directory '{str(output_dir).replace(os.sep, "/")}'.
Your task is to generate a detailed, step-by-step migration plan based on the provided Angular project context.

IMPORTANT RULES:
- The React project is ALWAYS a Single Page Application (SPA). DO NOT include any tasks related to Server-Side Rendering (SSR), server entrypoints, or SSR-specific configuration.
- You MUST preserve the same folder structure and file names from the Angular project in the new React project wherever possible. Only change structure or file names if it is required for React best practices or idiomatic usage (e.g., converting `.ts` to `.tsx` for components, or creating a `hooks` folder for React hooks). If you do change a structure or file name, clearly justify the change in the task description.
- Do NOT introduce new folders or files unless they are necessary for React (e.g., splitting out hooks, context, or provider files).
- The plan should be extremely detailed, as if guiding a junior engineer. Do not write general steps. Each task must be actionable and specific.
- **Visual Design and Styling**: The React project MUST replicate the visual design, layout, and styling of the original Angular project as closely as possible. All CSS, SCSS, or other styling solutions should be migrated to achieve visual parity.

Your output MUST include the following sections, in this order:

1.  **React File Tree**: A markdown code block showing the complete target folder and file structure for the new React application within the '{str(output_dir).replace(os.sep, "/")}' directory.
    Example:
    ```markdown
    ### React File Tree
    ```
    {str(output_dir).replace(os.sep, "/")}
    ├── public/
    │   └── vite.svg
    ├── src/
    │   ├── assets/
    │   │   └── react.svg
    │   ├── components/
    │   │   └── MyComponent/
    │   │       ├── MyComponent.tsx
    │   │       └── MyComponent.module.css
    │   ├── App.tsx
    │   ├── main.tsx
    │   └── ... (other files)
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    └── tsconfig.json
    ```
    ```

2.  **npm Packages**: A markdown code block listing ONLY the package names required for the React Vite + TS project (no version numbers).
    Example:
    ```markdown
    ### npm Packages
    (These are listed for informational purposes for the human user; do not create tasks to install them.)
    ```
    react-router-dom
    axios
    zustand
    ```
    ```

3.  **Migration Tasks**: A Markdown checklist of granular implementation tasks. Each task must reference specific file paths from the "React File Tree" you defined.
    IMPORTANT:
    - Do NOT include any generic "test", "documentation", or final verification steps.
    - Do NOT include any commands or steps such as 'cd …', 'npm install', 'pnpm add', or 'yarn add'.
    - Do NOT write tasks about installing packages or navigating into the React project directory. All paths should be relative to the root of the output directory ('{str(output_dir).replace(os.sep, "/")}').
    - Do NOT include any SSR-related tasks or files.
    - Do NOT include any tasks related to writing documentation or README.
    - Do NOT write Update `README.md` task.
    - Unless absolutely necessary for React, keep the folder structure and file names the same as the Angular project.
    Output format for each task:
    - [ ] TASK_ID (e.g., T01, T02)
      - description: A clear, concise, and exact instruction for the junior engineer agent. For example: "Create src/components/TodoItem/TodoItem.tsx and implement the basic structure based on Angular's todo-card.component.ts." or "Modify src/App.tsx to import and render the new Header component."

Angular Project Context (from '{str(input_dir).replace(os.sep, "/")}'):
{angular_project_context}

Generate the migration plan:
"""
        try:
            console.print("💬 [bold blue]PlannerAgent: Sending request to Gemini API...[/]")
            with console.status("[bold green]🧠 Thinking... (waiting for Gemini LLM response)[/]", spinner="dots"):
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                plan_markdown = "".join(part.text for part in response.candidates[0].content.parts)
                console.print("✅ [bold green]PlannerAgent: Plan generation complete (via LLM).[/]")
                
                if not plan_markdown.lstrip().startswith("#"):
                    plan_markdown = "# Migration Plan (Generated by LLM)\n\n" + plan_markdown
                return plan_markdown
            else:
                console.print("⚠️ [bold yellow]PlannerAgent: LLM response was empty or malformed. Using fallback plan.[/]")
                
                if response:
                    console.print(f"⚠️ [yellow]PlannerAgent: Problematic LLM response details:[/] [dim]{response}[/]")
                return self._generate_fallback_plan(output_dir, input_dir)

        except Exception as e:
            console.print(f"❌ [bold red]PlannerAgent: Error during LLM call:[/] [red]{e}[/]")
            traceback.print_exc()
            console.print("⚠️ [bold yellow]PlannerAgent: Using fallback plan due to LLM error.[/]")
            return self._generate_fallback_plan(output_dir, input_dir)
