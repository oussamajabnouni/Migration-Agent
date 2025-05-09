from pathlib import Path
import subprocess
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai 
from google.genai import types 
import time 


def read_file(path: str) -> str:
    """Reads the content of a file at the given path relative to the current working directory."""
    print(f"\n Tool: Reading file: {path}")
    try:
        
        cwd = Path(os.getcwd())
        target_path = (cwd / path).resolve()
        
        if not target_path.is_relative_to(cwd):
            return "Error: Access denied. Path is outside the current working directory."
        if not target_path.is_file():
            return f"Error: File not found at {path}"
        return target_path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"

def list_files(directory: str) -> str:
    """Lists files in the specified directory relative to the current working directory."""
    print(f"\n Tool: Listing files in directory: {directory}")
    try:
        cwd = Path(os.getcwd())
        target_dir = (cwd / directory).resolve()
        
        if not target_dir.is_relative_to(cwd):
            return "Error: Access denied. Path is outside the current working directory."
        if not target_dir.is_dir():
            return f"Error: Directory not found at {directory}"

        files = [f.name for f in target_dir.iterdir()]
        return "\n".join(files) if files else "No files found."
    except Exception as e:
        return f"Error listing files: {e}"

def edit_file(path: str, content: str) -> str:
    """Writes or overwrites content to a file at the given path relative to the current working directory."""
    print(f"\n Tool: Editing file: {path}")
    try:
        
        cwd = Path(os.getcwd())
        target_path = (cwd / path).resolve()
        if not target_path.is_relative_to(cwd):
            return "Error: Access denied. Path is outside the current working directory."

        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content)
        return f"File '{path}' saved successfully."
    except Exception as e:
        return f"Error writing file: {e}"

def execute_bash_command(command: str) -> str:
    """
    Executes any bash command in the current working directory.

    Args:
        command: The full bash command string to execute.

    Returns:
        The standard output and standard error of the command, or an error message.
    """
    print(f"\n Tool: Executing bash command: {command}")

    

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd(), 
            check=False 
        )
        if result.stdout:
            print(f"\n Command Output (stdout):\n{result.stdout.strip()}")
        output = f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n--- Command exited with code: {result.returncode} ---"
        return output.strip()

    except Exception as e:
        return f"Error executing command '{command}': {e}"

def get_current_date_and_time(timezone: str) -> str:
    """Returns the current date and time as ISO 8601 string in the specified timezone. Default is PST (America/Los_Angeles) if an invalid timezone is provided."""
    try:
        print(f"\n Tool: Getting current date and time for timezone: {timezone}")
        tz = ZoneInfo(timezone)
    except Exception as e:
        print(f"Error: Invalid timezone '{timezone}' provided. Using default: America/Los_Angeles")
        tz = ZoneInfo('America/Los_Angeles')
    now = datetime.now(tz)
    return now.isoformat()

def upload_pdf_for_gemini(pdf_path_str: str) -> types.File | None:
    """
    Uploads a PDF file relative to the project root to Google Gemini
    using the File API and waits for it to be processed.

    Args:
        pdf_path_str: The path to the PDF file, relative to the project root.

    Returns:
        A google.generativeai.types.File object if successful, None otherwise.
        Prints errors to console.
    """
    
    
    global project_root
    if 'project_root' not in globals():
         
         project_root = Path(__file__).resolve().parents[1]
         print("⚠️ 'project_root' was not defined globally in tools.py, attempting definition.")
         

    try:
        target_path = (project_root / pdf_path_str).resolve()

        
        if not target_path.is_relative_to(project_root):
            print(f"\n Error: Access denied. Path '{pdf_path_str}' is outside the project directory.")
            return None
        if not target_path.is_file():
            print(f"\n Error: PDF file not found at resolved path '{target_path}'")
            return None
        if target_path.suffix.lower() != ".pdf":
            print(f"\n Error: File '{target_path.name}' is not a PDF.")
            return None

        print(f"\n Uploading '{target_path.name}'...")
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print(f"\n[31mError: GEMINI_API_KEY environment variable not set.\nPlease export your API key before uploading PDFs.[0m")
            return None
        client = genai.Client(api_key=api_key)

        
        pdf_file = client.files.upload(file=target_path)
        print(f" Uploaded '{pdf_file.display_name}' as: {pdf_file.name}")
        print("⏳ Waiting for processing...")

        
        start_time = time.time()
        timeout_seconds = 120 
        while pdf_file.state.name == "PROCESSING":
            if time.time() - start_time > timeout_seconds:
                 print(f"\n Error: File processing timed out after {timeout_seconds} seconds for {pdf_file.name}.")
                 
                 try:
                     client.files.delete(name=pdf_file.name)
                     print(f"🧹 Cleaned up timed-out file: {pdf_file.name}")
                 except Exception as delete_e:
                     print(f"⚠️ Could not delete timed-out file {pdf_file.name}: {delete_e}")
                 return None

            time.sleep(5) 
            pdf_file = client.files.get(name=pdf_file.name) 
            print(f"   Current state: {pdf_file.state.name}")

        if pdf_file.state.name == "ACTIVE":
            print(f" File '{pdf_file.display_name}' is ready.")
            return pdf_file
        else:
            print(f"\n Error: File processing failed for '{pdf_file.display_name}'. Final State: {pdf_file.state.name}")
            
            try:
                 client.files.delete(name=pdf_file.name)
                 print(f"🧹 Cleaned up failed file: {pdf_file.name}")
            except Exception as delete_e:
                 print(f"⚠️ Could not delete failed file {pdf_file.name}: {delete_e}")
            return None

    except Exception as e:
        print(f"\n An error occurred during PDF upload/processing: {e}")
        
        if 'pdf_file' in locals() and hasattr(pdf_file, 'name'):
             try:
                 print(f"🧹 Attempting to delete potentially failed upload: {pdf_file.name}")
                 client.files.delete(name=pdf_file.name)
             except Exception as delete_e:
                 print(f"⚠️ Could not delete file during error cleanup: {delete_e}")
        return None
