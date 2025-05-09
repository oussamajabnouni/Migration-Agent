import os
from pathlib import Path
from typing import Tuple, List, Callable, Dict, Any 

from google.genai import types as genai_types
from rich.console import Console

console = Console()


from src.base import CodeAgent 
from domain.task import Task 
from tools import execute_bash_command as tools_execute_bash_command 

class CodingAgent:
    """
    The CodingAgent executes a single migration task using an underlying LLM agent (CodeAgent).
    It ensures that all tool operations (file access, command execution) are sandboxed
    within the defined project directories (input/ and output/).
    """
    def __init__(self, base_gemini_agent: CodeAgent, sandbox_dir: Path):
        """
        Initializes the CodingAgent.

        Args:
            base_gemini_agent: An instance of the base CodeAgent, configured with API keys and model.
            sandbox_dir: The root directory for sandboxed operations.
        """
        self.base_agent = base_gemini_agent
        self.sandbox_dir = sandbox_dir.resolve()
        self.output_dir = (self.sandbox_dir / "output").resolve()
        self.input_dir = (self.sandbox_dir / "input").resolve()

        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)

        
        self.base_agent.tool_functions_map = {
            f.__name__: f for f in self.base_agent.tool_functions
        }
        self._sandboxed_tool_functions = self._create_sandboxed_tools(self.base_agent.tool_functions)

    def _resolve_sandbox_path(self, relative_path: str, context_dir_type: str) -> Path:
        """
        Resolves a path provided by the LLM (relative to 'input/' or 'output/')
        to an absolute path within the correct sandbox subdirectory.
        Raises PermissionError if the path attempts to escape the sandbox.
        """
        base_dir = self.output_dir 
        path_to_resolve = relative_path

        if context_dir_type == "input":
            base_dir = self.input_dir
            if relative_path.startswith("input/"): 
                path_to_resolve = relative_path[len("input/"):]
        elif context_dir_type == "output":
            base_dir = self.output_dir
            if relative_path.startswith("output/"): 
                path_to_resolve = relative_path[len("output/"):]
        else: 
            raise ValueError(f"Invalid context_dir_type: {context_dir_type}")

        
        
        if ".." in Path(path_to_resolve).parts:
             
             pass 

        abs_path = (base_dir / path_to_resolve).resolve()

        
        if not abs_path.is_relative_to(base_dir) and abs_path != base_dir :
             
            raise PermissionError(
                f"Path '{relative_path}' (resolved to '{abs_path}') is outside the allowed directory '{base_dir}'."
            )
        return abs_path

    def _get_path_relative_to_cwd(self, absolute_sandboxed_path: Path) -> str:
        """
        Converts an absolute path within the sandbox to a path string relative
        to the current working directory (project_root), as expected by original tools.
        """
        return os.path.relpath(absolute_sandboxed_path, Path(os.getcwd()))

    
    def _sandboxed_read_file(self, path: str) -> str:
        try:
            context_type = "input"
            if path.startswith("output/"):
                context_type = "output"
            elif not path.startswith("input/"):
                return "Error: `read_file` path must be prefixed with 'input/' or 'output/'."
            
            abs_path = self._resolve_sandbox_path(path, context_type)
            path_for_tool = self._get_path_relative_to_cwd(abs_path)
            return self.base_agent.tool_functions_map['read_file'](path_for_tool)
        except PermissionError as e: return str(e)
        except Exception as e: return f"Error in sandboxed_read_file: {type(e).__name__} {e}"

    def _sandboxed_edit_file(self, path: str, content: str) -> str:
        try:
            if not path.startswith("output/"):
                return "Error: `edit_file` path must be prefixed with 'output/'."
            abs_path = self._resolve_sandbox_path(path, "output")
            path_for_tool = self._get_path_relative_to_cwd(abs_path)
            return self.base_agent.tool_functions_map['edit_file'](path_for_tool, content)
        except PermissionError as e: return str(e)
        except Exception as e: return f"Error in sandboxed_edit_file: {type(e).__name__} {e}"

    def _sandboxed_list_files(self, directory: str) -> str:
        try:
            context_type = "input"
            if directory.startswith("output/"):
                context_type = "output"
            elif not directory.startswith("input/"):
                 
                if directory == "input" or directory == "input/": 
                    pass 
                elif directory == "output" or directory == "output/": 
                     pass
                else:
                    return "Error: `list_files` directory must be prefixed with 'input/' or 'output/' (or be 'input' or 'output')."

            abs_path = self._resolve_sandbox_path(directory, context_type)
            path_for_tool = self._get_path_relative_to_cwd(abs_path)
            return self.base_agent.tool_functions_map['list_files'](path_for_tool)
        except PermissionError as e: return str(e)
        except Exception as e: return f"Error in sandboxed_list_files: {type(e).__name__} {e}"

    def _sandboxed_execute_bash_command(self, command: str) -> str:
        try:
            
            
            
            
            
            
            sandboxed_command = f"cd \"{str(self.output_dir)}\" && {command}"
            return self.base_agent.tool_functions_map['execute_bash_command'](sandboxed_command)
        except Exception as e:
            return f"Error in sandboxed_execute_bash_command: {type(e).__name__} {e}"

    def _create_sandboxed_tools(self, original_tool_functions: List[Callable]) -> List[Callable]:
        from google.genai import types as genai_types

        sandboxed_tools = []
        tool_map = {
            "read_file": self._sandboxed_read_file,
            "edit_file": self._sandboxed_edit_file,
            "list_files": self._sandboxed_list_files,
            "execute_bash_command": self._sandboxed_execute_bash_command,
        }

        for original_func_def in original_tool_functions:
            original_name = original_func_def.__name__
            original_doc = original_func_def.__doc__

            if original_name == "execute_bash_command":
                def tool_executable(command: str):
                    return tool_map["execute_bash_command"](command)
                tool_executable.__name__ = "execute_bash_command"
                tool_executable.__doc__ = (
                    "Executes any bash command in the 'output/' directory. "
                    "Use for creating directories (mkdir -p), moving files (mv), etc. "
                    "All commands are executed relative to the 'output/' directory. "
                    "Argument: command (str): The full bash command string to execute."
                )
                tool_schema = genai_types.FunctionDeclaration(
                    name="execute_bash_command",
                    description=tool_executable.__doc__,
                    parameters=genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        properties={
                            "command": genai_types.Schema(
                                type=genai_types.Type.STRING,
                                description="The full bash command string to execute."
                            )
                        },
                        required=["command"]
                    )
                )
                tool_executable._function_declaration = tool_schema
                sandboxed_tools.append(tool_executable)
            elif original_name == "read_file":
                def tool_executable(path: str):
                    return tool_map["read_file"](path)
                tool_executable.__name__ = "read_file"
                tool_executable.__doc__ = (
                    "Reads the content of a file. Path must start with 'input/' or 'output/'. "
                    "Argument: path (str): Path to the file (e.g., 'input/src/file.ts')."
                )
                tool_schema = genai_types.FunctionDeclaration(
                    name="read_file",
                    description=tool_executable.__doc__,
                    parameters=genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        properties={
                            "path": genai_types.Schema(
                                type=genai_types.Type.STRING,
                                description="Path to the file (e.g., 'input/src/file.ts')."
                            )
                        },
                        required=["path"]
                    )
                )
                tool_executable._function_declaration = tool_schema
                sandboxed_tools.append(tool_executable)
            elif original_name == "edit_file":
                def tool_executable(path: str, content: str):
                    return tool_map["edit_file"](path, content)
                tool_executable.__name__ = "edit_file"
                tool_executable.__doc__ = (
                    "Writes or overwrites content to a file. Path must start with 'output/'. "
                    "Arguments: path (str): Path to the file (e.g., 'output/src/file.tsx'). content (str): New content for the file."
                )
                tool_schema = genai_types.FunctionDeclaration(
                    name="edit_file",
                    description=tool_executable.__doc__,
                    parameters=genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        properties={
                            "path": genai_types.Schema(
                                type=genai_types.Type.STRING,
                                description="Path to the file (e.g., 'output/src/file.tsx')."
                            ),
                            "content": genai_types.Schema(
                                type=genai_types.Type.STRING,
                                description="New content for the file."
                            )
                        },
                        required=["path", "content"]
                    )
                )
                tool_executable._function_declaration = tool_schema
                sandboxed_tools.append(tool_executable)
            elif original_name == "list_files":
                def tool_executable(directory: str):
                    return tool_map["list_files"](directory)
                tool_executable.__name__ = "list_files"
                tool_executable.__doc__ = (
                    "Lists files in a directory. Path must start with 'input/' or 'output/'. "
                    "Argument: directory (str): Directory path (e.g., 'input/src/components')."
                )
                tool_schema = genai_types.FunctionDeclaration(
                    name="list_files",
                    description=tool_executable.__doc__,
                    parameters=genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        properties={
                            "directory": genai_types.Schema(
                                type=genai_types.Type.STRING,
                                description="Directory path (e.g., 'input/src/components')."
                            )
                        },
                        required=["directory"]
                    )
                )
                tool_executable._function_declaration = tool_schema
                sandboxed_tools.append(tool_executable)
            else:
                sandboxed_tools.append(original_func_def)
        return sandboxed_tools

    def _run_lint_and_typecheck(self) -> Tuple[bool, str, str]:
        """
        Runs lint and typecheck commands in the output directory.
        Returns (success, lint_errors, type_errors)
        """
        lint_result = self._sandboxed_execute_bash_command("npm run lint")
        typecheck_result = self._sandboxed_execute_bash_command("npm run typecheck")

        def parse_result(result: str):
            
            code = 0
            if "Command exited with code:" in result:
                try:
                    code = int(result.split("Command exited with code:")[1].split("---")[0].strip())
                except Exception:
                    code = 1
            return code, result

        lint_code, lint_errors = parse_result(lint_result)
        type_code, type_errors = parse_result(typecheck_result)
        success = (lint_code == 0 and type_code == 0)
        return success, lint_errors, type_errors

    def execute_task(self, task: Task, full_plan_markdown: str) -> Tuple[bool, str]:
        """
        Executes a given migration task, with the full migration plan as context.

        Args:
            task: A Task object (assumed to have .id and .description attributes).
            full_plan_markdown: The full migration plan in Markdown, for context.

        Returns:
            A tuple (success: bool, notes: str).
        """
        console.print(f"🤖 [bold blue]CodingAgent: Executing Task ID:[/] [cyan]{task.id}[/] - [bold]Description:[/] [magenta]{task.description}[/]")

        
        
        execute_bash_tool_func = self.base_agent.tool_functions_map.get('execute_bash_command')
        if execute_bash_tool_func and hasattr(execute_bash_tool_func, '__doc__') and execute_bash_tool_func.__doc__:
            allowed_commands_doc = execute_bash_tool_func.__doc__
        else:
            
            allowed_commands_doc = getattr(tools_execute_bash_command, '__doc__', 'ls, cat, git add/status/commit/push')
        
        allowed_commands_doc = allowed_commands_doc.strip() 

        prompt = f"""
You are an AI coding assistant migrating an Angular project to React.

**Design Fidelity**: When implementing this task, ensure that the visual design, layout, and styling of the original Angular component/feature are replicated as closely as possible in the React equivalent. Refer to the Angular project's styling and structure to maintain visual consistency.

**Overall Migration Plan Context:**
```markdown
{full_plan_markdown}
```

**Your current specific task is: {task.id} - {task.description}.**

You operate in a sandboxed environment:
- Angular project (read-only): 'input/' directory.
- React project (writable): 'output/' directory.

**CRITICAL TOOL USAGE RULES:**
1.  `read_file(path: str)`:
    - For Angular files: `path` MUST start with `input/` (e.g., `input/src/app.module.ts`).
    - For React files: `path` MUST start with `output/` (e.g., `output/src/MyComponent.tsx`).
2.  `edit_file(path: str, content: str)`:
    - For React files: `path` MUST start with `output/` (e.g., `output/package.json`).
    - DO NOT use for 'input/' files.
3.  `list_files(directory: str)`:
    - For Angular files: `directory` MUST start with `input/` (e.g., `input/src/components`).
    - For React files: `directory` MUST start with `output/` (e.g., `output/public`).
    - You can also use `input` or `output` to list the roots of these directories.
4.  `execute_bash_command(command: str)`:
    - Commands run inside the 'output/' directory.
    - Example: `execute_bash_command(command='npm install react')`.
    - Allowed command patterns: {allowed_commands_doc}

Strictly follow these path prefix rules. Incorrect paths will cause errors.
Focus on completing ONLY the current specific task: "{task.description}".
Consider the overall plan for context, but only implement the current task.
Your generated code will be subsequently checked for linting and TypeScript errors. Please ensure your code is clean and adheres to common best practices to pass these checks.
Summarize your actions for the current task. If unable, explain why.
        """

        if not self.base_agent.client:
            self.base_agent._configure_client() 

        
        try:
            self.base_agent.chat = self.base_agent.client.chats.create(
                model=self.base_agent.model_name,
                history=[] 
            )
        except Exception as e:
            error_msg = f"CodingAgent: Error initializing chat session: {e}"
            console.print(f"❌ [bold red]{error_msg}[/]")
            return False, error_msg

        
        default_thinking_budget = 256 
        thinking_budget = getattr(self.base_agent, 'thinking_budget', default_thinking_budget)
        task_thinking_config = genai_types.ThinkingConfig(thinking_budget=thinking_budget)
        
        task_tool_config = genai_types.GenerateContentConfig(
            tools=self._sandboxed_tool_functions, 
            thinking_config=task_thinking_config
        )

        import time
        from google.api_core import exceptions as google_exceptions
        import traceback

        max_retries = 3
        retry_delay_seconds = 5

        
        for attempt in range(max_retries):
            try:
                console.print(f"💬 [bold blue]CodingAgent: Sending task to LLM (Attempt {attempt + 1}/{max_retries}).[/] [magenta]Task:[/] [italic]{task.description}[/]")
                with console.status("[bold green]🧠 Thinking... (waiting for Gemini LLM response)[/]", spinner="dots"):
                    response = self.base_agent.chat.send_message(
                        message=[prompt],
                        config=task_tool_config
                    )

                response_text = ""
                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    response_text = " ".join(p.text for p in response.candidates[0].content.parts if hasattr(p, 'text') and p.text)
                
                console.print(f"📝 [dim]CodingAgent: LLM raw response text:[/]\n[dim]{response_text}[/]")

                
                if response_text.strip().startswith("Error:") or \
                   any(kw in response_text.lower() for kw in ["unable to complete", "task failed", "could not perform", "i am unable", "i cannot"]):
                    console.print(f"❌ [bold red]CodingAgent: Task indicated failure by LLM.[/] [red]LLM Response:[/] [dim]{response_text}[/]")
                    return False, f"Task execution failed or LLM reported an issue: {response_text}"

                break  

            except google_exceptions.InternalServerError as e:  
                console.print(f"⚠️ [bold yellow]CodingAgent: InternalServerError (HTTP 500) on attempt {attempt + 1}/{max_retries}:[/] [yellow]{e}[/]")
                if attempt < max_retries - 1:
                    console.print(f"⏳ [dim]Retrying in {retry_delay_seconds}s...[/]")
                    time.sleep(retry_delay_seconds)
                else:
                    console.print("❌ [bold red]CodingAgent: Max retries reached for InternalServerError.[/]")
                    error_msg = f"CodingAgent: InternalServerError after {max_retries} attempts for task '{task.id}': {e}\n{traceback.format_exc()}"
                    return False, error_msg
            except Exception as e:
                error_msg = f"CodingAgent: Non-retryable exception during LLM interaction for task '{task.id}': {type(e).__name__} - {e}\n{traceback.format_exc()}"
                console.print(f"❌ [bold red]{error_msg}[/]")
                return False, error_msg

        
        fix_iteration = 0
        notes = f"Initial LLM response:\n{response_text}\n"
        llm_gave_up_keywords = [
            "unable to fix", "cannot resolve", "cannot be fixed", "false positive and i cannot proceed",
            "i am unable", "i cannot", "no further fix", "stuck", "not possible", "not enough information"
        ]
        while True:
            success, lint_errors, type_errors = self._run_lint_and_typecheck()
            if success:
                notes += f"\nLint and typecheck passed after {fix_iteration} fix iterations."
                return True, notes
            notes += f"\n--- Lint Errors (iteration {fix_iteration+1}) ---\n{lint_errors}\n"
            notes += f"\n--- TypeScript Errors (iteration {fix_iteration+1}) ---\n{type_errors}\n"

            
            fix_prompt = f"""
The previous attempt to complete the task "{task.description}" resulted in the following linting and/or TypeScript errors:

--- Lint Errors ---
{lint_errors}

--- TypeScript Errors ---
{type_errors}

Please analyze these errors and provide the necessary code changes to fix ONLY these reported errors using the `edit_file` tool.
Do not re-implement the entire task or introduce new features.
Focus solely on resolving the listed errors.
If you believe an error is a false positive or cannot be fixed with the available information, please state that clearly.
"""
            try:
                with console.status("[bold green]🧠 Thinking... (waiting for Gemini LLM response)[/]", spinner="dots"):
                    fix_response = self.base_agent.chat.send_message(
                        message=[fix_prompt],
                        config=task_tool_config
                    )
                fix_response_text = ""
                if fix_response.candidates and fix_response.candidates[0].content and fix_response.candidates[0].content.parts:
                    fix_response_text = " ".join(p.text for p in fix_response.candidates[0].content.parts if hasattr(p, 'text') and p.text)
                notes += f"\n--- LLM Fix Attempt {fix_iteration+1} ---\n{fix_response_text}\n"
                
                if any(keyword in fix_response_text.lower() for keyword in llm_gave_up_keywords):
                    notes += "\nLLM indicated it cannot fix the remaining errors."
                    console.print(f"⚠️ [bold yellow]CodingAgent: LLM indicated it cannot fix the errors. Halting fix attempts.[/]")
                    break
            except Exception as e:
                notes += f"\nException during LLM fix attempt {fix_iteration+1}: {e}\n"
                break

            fix_iteration += 1

        
        notes += f"\nLint and/or typecheck errors remain after {fix_iteration} fix attempts. Task failed."
        return False, notes

if __name__ == '__main__':
    
    
    

    console.print("🧪 [bold blue]CodingAgent direct execution (for testing - requires setup).[/]")
