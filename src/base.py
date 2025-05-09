from google import genai
from google.genai import types
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from src.tools import (
    read_file, list_files, edit_file, execute_bash_command,
    get_current_date_and_time, upload_pdf_for_gemini
)
import traceback
import argparse
import functools
import logging

MODEL_NAME = "gemini-2.5-flash-preview-04-17"
DEFAULT_THINKING_BUDGET = 256

class CodeAgent:

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-preview-04-17", verbose: bool = False):
        self.api_key = api_key
        self.verbose = verbose
        self.model_name = f'models/{model_name}' 
        
        self.tool_functions = [
            read_file,
            list_files,
            edit_file,
            execute_bash_command,
            get_current_date_and_time,
            upload_pdf_for_gemini
        ]
        if self.verbose:
            self.tool_functions = [self._make_verbose_tool(f) for f in self.tool_functions]
        self.client = None
        self.chat = None
        self.conversation_history = [] 
        self.current_token_count = 0 
        self.active_files = [] 
        self._configure_client()

    def _configure_client(self):
        print("\n Configuring genai client...")
        try:
            
            self.client = genai.Client(api_key=self.api_key)
            print(" Client configured successfully.")
        except Exception as e:
            print(f" Error configuring genai client: {e}")
            traceback.print_exc()
            sys.exit(1)

    def start_interaction(self):
        if not self.client:
            print("\n Client not configured. Exiting.")
            return

        print("\n Initializing chat session...")
        try:
            
            self.chat = self.client.chats.create(model=self.model_name, history=[])
            print(" Chat session initialized.")
        except Exception as e:
            print(f" Error initializing chat session: {e}")
            traceback.print_exc()
            sys.exit(1)

        print("\n Agent ready. Ask me anything. Type '/exit' or '/q' to quit.")
        print("   Use '/upload <path/to/file.pdf>' to seed PDF into context.")
        print("   Use '/reset' to clear the chat and start fresh.")

        
        try:
            budget_input = input(f"Enter thinking budget (0 to 24000) for this session [{DEFAULT_THINKING_BUDGET}]: ").strip()
            self.thinking_budget = int(budget_input) if budget_input else DEFAULT_THINKING_BUDGET
        except ValueError:
            print(f"⚠️ Invalid thinking budget. Using default of {DEFAULT_THINKING_BUDGET}.")
            self.thinking_budget = DEFAULT_THINKING_BUDGET
        self.thinking_config = types.ThinkingConfig(thinking_budget=self.thinking_budget)

        tool_config = types.GenerateContentConfig(tools=self.tool_functions, thinking_config=self.thinking_config)

        while True:
            try:
                
                
                active_files_info = f" [{len(self.active_files)} files]" if self.active_files else ""
                prompt_text = f"\n🔵 You ({self.current_token_count}{active_files_info}): "
                user_input = input(prompt_text).strip()

                if user_input.lower() in ["exit", "quit", "/exit", "/quit", "/q"]:
                    print("\n👋 Goodbye!")
                    break
                if not user_input:
                    continue

                
                if user_input.lower().startswith("/upload "):
                    pdf_path_str = user_input[len("/upload "):].strip()
                    if pdf_path_str:
                        
                        if not self.client:
                             self._configure_client()
                             if not self.client:
                                 print("\n Cannot upload: genai client not configured.")
                                 continue 
                        
                        uploaded_file = upload_pdf_for_gemini(pdf_path_str)
                        if uploaded_file:
                            print("\n⚒️ Extracting text from PDF to seed context...")
                            extraction_response = self.chat.send_message(
                                message=[uploaded_file, "\n\nExtract the entire text of this PDF, organized by section. Include all tables, and figures (full descriptions where appropriate in place of images)."],
                                config=tool_config
                            )
                            extraction_content = extraction_response.candidates[0].content
                            self.conversation_history.append(extraction_content)
                            
                            self.active_files = []
                            print("\n✅ PDF context seeded.")
                        
                    else:
                        print("\n⚠️ Usage: /upload <relative/path/to/your/file.pdf>")
                    continue 

                elif user_input.lower() == "/reset":
                    print("\n🎯 Resetting context and starting a new chat session...")
                    self.chat = self.client.chats.create(model=self.model_name, history=[])
                    self.conversation_history = []
                    self.current_token_count = 0
                    print("\n✅ Chat session and history cleared.")
                    continue 

                
                message_content = [user_input] 
                if self.active_files:
                    message_content.extend(self.active_files) 
                    if self.verbose:
                        print(f"\n📎 Attaching {len(self.active_files)} files to the prompt:")
                        for f in self.active_files:
                            print(f"   - {f.display_name} ({f.name})")

                
                
                
                new_user_content = types.Content(parts=[types.Part(text=user_input)], role="user")
                self.conversation_history.append(new_user_content)

                
                print("\n⏳ Sending message and processing...")
                
                tool_config = types.GenerateContentConfig(tools=self.tool_functions, thinking_config=self.thinking_config)

                
                
                response = self.chat.send_message(
                    message=message_content, 
                    config=tool_config
                )

                
                agent_response_content = None
                response_text = "" 
                if response.candidates and response.candidates[0].content:
                    agent_response_content = response.candidates[0].content
                    
                    if agent_response_content.parts:
                         
                         response_text = " ".join(p.text for p in agent_response_content.parts if hasattr(p, 'text'))
                    self.conversation_history.append(agent_response_content)
                else:
                    print("\n⚠️ Agent response did not contain content for history/counting.")

                
                
                print(f"\n🟢 [92mAgent:[0m {response_text or response.text}")

                
                try:
                    
                    token_count_response = self.client.models.count_tokens(
                        model=self.model_name,
                        contents=self.conversation_history
                    )
                    self.current_token_count = token_count_response.total_tokens
                except Exception as count_error:
                    
                    print(f"\n⚠️ [93mCould not update token count: {count_error}[0m")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n🔴 [91mAn error occurred during interaction: {e}[0m")
                traceback.print_exc() 

    def _make_verbose_tool(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"\n🔧 Tool called: {func.__name__}, args: {args}, kwargs: {kwargs}")
            result = func(*args, **kwargs)
            print(f"\n▶️ Tool result ({func.__name__}): {result}")
            return result
        return wrapper
