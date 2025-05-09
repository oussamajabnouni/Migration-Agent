import os
import subprocess
from pathlib import Path
from google import genai
from rich.console import Console

console = Console()

class PackagingAgent:
    """
    PackagingAgent uses Gemini to extract npm package names from a plan.md and runs the pnpm install command in the output directory.
    """
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash-preview-04-17", output_dir: Path = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                console.print(f"❌ [bold red]PackagingAgent: Error initializing Google GenAI client:[/] [red]{e}[/]")
                self.client = None
        else:
            console.print("⚠️ [bold yellow]PackagingAgent: GEMINI_API_KEY not found. LLM features will be disabled.[/]")

    def _generate_install_command(self, plan_markdown: str) -> str:
        """
        Uses Gemini to extract npm package names from the plan and generate a pnpm install command.
        Returns the command string, or "NO_PACKAGES_FOUND".
        """
        if not self.client:
            console.print("⚠️ [bold yellow]PackagingAgent: LLM client not available.[/]")
            return "NO_PACKAGES_FOUND"

        prompt = f"""
You are an expert pnpm packaging assistant.
Given the following migration plan in Markdown, extract all package names listed under the '### npm Packages' section.
Construct a single pnpm install command to install all these packages as dependencies.
If the packages are 'react', 'axios', 'zustand', the command should be 'pnpm install react axios zustand'.
If no packages are listed, return exactly 'NO_PACKAGES_FOUND'.
Return ONLY the command string or 'NO_PACKAGES_FOUND'. Do not include any other text, markdown, or explanation.

Migration Plan:
{plan_markdown}
"""
        try:
            with console.status("[bold green]🧠 Thinking... (waiting for Gemini LLM response)[/]", spinner="dots"):
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            
            command = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                command = "".join(part.text for part in response.candidates[0].content.parts).strip()
            
            command = command.replace("```", "").replace("bash", "").replace("shell", "").strip()
            if command.lower() == "no_packages_found":
                return "NO_PACKAGES_FOUND"
            if command.startswith("pnpm install"):
                return command
            
            if command and not command.startswith("pnpm"):
                return "pnpm install " + command
            return "NO_PACKAGES_FOUND"
        except Exception as e:
            console.print(f"❌ [bold red]PackagingAgent: Error during LLM call:[/] [red]{e}[/]")
            return "NO_PACKAGES_FOUND"

    def install_packages_from_plan(self, plan_markdown: str) -> bool:
        """
        Extracts pnpm install command from plan and runs it in the output directory.
        Returns True if successful or no packages, False if install fails.
        """
        install_command = self._generate_install_command(plan_markdown)
        if install_command == "NO_PACKAGES_FOUND":
            console.print("ℹ️ [bold blue]PackagingAgent: No npm packages listed for installation in the plan.[/]")
            return True

        console.print(f"🚀 [bold blue]PackagingAgent: Running in[/] [italic magenta]{self.output_dir.resolve()}[/]: [green]{install_command}[/]")
        try:
            result = subprocess.run(
                install_command,
                shell=True,
                cwd=self.output_dir,
                check=True
            )
            console.print("✅ [bold green]PackagingAgent: pnpm install successful.[/]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"❌ [bold red]PackagingAgent: Error during pnpm install command execution in[/] [italic magenta]{self.output_dir}[/]:")
            console.print(f"🔸 [red]Command:[/] [dim]{e.cmd}[/]")
            console.print(f"🔸 [red]Return code:[/] [dim]{e.returncode}[/]")
            console.print(f"🔸 [red]Stdout:[/] [dim]{e.stdout}[/]")
            console.print(f"🔸 [red]Stderr:[/] [dim]{e.stderr}[/]")
            console.print("⏹️ [bold yellow]PackagingAgent: Halting due to package installation failure.[/]")
            return False
        except Exception as e:
            console.print(f"❌ [bold red]PackagingAgent: Unexpected error during pnpm install:[/] [red]{e}[/]")
            return False
