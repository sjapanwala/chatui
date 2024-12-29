#!/usr/bin/env python3

from sys import exception
from ollama import chat
from ollama import ChatResponse
import threading
import time
import os
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich import print as rprint
import getpass
import json
from datetime import datetime
import subprocess

AI_NAME = "ChatTUI"

# Default system prompt that defines the AI's behavior and context
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant named ChatTUI. You aim to be concise, 
accurate, and helpful in your responses. You should maintain a friendly and professional tone while
engaging with users."""


def create_spinner(message=f"{AI_NAME} is Thinking"):
    """Create and return spinner control functions"""
    console = Console()
    stop_event = threading.Event()
    
    def spinner_function():
        with console.status(message, spinner="dots") as status:
            while not stop_event.is_set():
                time.sleep(0.1)
    
    def start_spinner():
        thread = threading.Thread(target=spinner_function)
        thread.start()
        return thread, stop_event
    
    def stop_spinner(thread, stop_event):
        stop_event.set()
        thread.join()
    
    return start_spinner, stop_spinner

def render_markdown(text):
    """Render markdown text in the terminal"""
    console = Console()
    md = Markdown(text)
    console.print(md)

def get_ai_response(conversation):
    """Get response from AI model with spinner"""
    start_spinner, stop_spinner = create_spinner()
    thread, stop_event = start_spinner()
    
    try:
        response = chat(
            model='llama3.2',
            messages=conversation
        )
        stop_spinner(thread, stop_event)
        return response['message']['content']
    except Exception as e:
        stop_spinner(thread, stop_event)
        raise e

def save_conversation_to_file(conversation, filename=None):
    """
    Save the conversation to a user-specified file
    Returns the filename used for saving
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = input(f"\nEnter filename to save conversation (default: conversation_{timestamp}.json): ").strip()
        if not filename:
            filename = f"conversation_{timestamp}.json"
        if not filename.endswith('.json'):
            filename += '.json'

    try:
        with open(filename, 'w') as f:
            json.dump(conversation, f, indent=2)
        rprint(f"\n[bold green]Conversation saved to {filename}[/bold green]")
        #subprocess.run(['mv', filename, f'~/.chatui/saved_conversations/{filename}'])
        return filename
    except Exception as e:
        rprint(f"\n[bold red]Error saving conversation: {str(e)}[/bold red]")
        return None

def load_conversation_from_file(filename):
    """
    Load a conversation from a file
    """
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        rprint(f"\n[bold red]Error loading conversation: {str(e)}[/bold red]")
        return []

def read_memory(filename):
    """
    Read and display the contents of a saved conversation file
    Returns a summary of the conversation
    """
    try:
        with open(filename, 'r') as f:
            conversation = json.load(f)
        
        rprint("\n[bold blue]Conversation Summary:[/bold blue]")
        message_count = len(conversation)
        user_messages = sum(1 for msg in conversation if msg['role'] == 'user')
        ai_messages = sum(1 for msg in conversation if msg['role'] == 'assistant')
        
        rprint(f"Total messages: {message_count}")
        rprint(f"User messages: {user_messages}")
        rprint(f"AI messages: {ai_messages}")
        
        # Display the last few exchanges
        if message_count > 0:
            rprint("\n[bold blue]Last few exchanges:[/bold blue]")
            start_idx = max(0, message_count - 4)  # Show last 2 exchanges (4 messages)
            for msg in conversation[start_idx:]:
                role = "[bold green]User[/bold green]" if msg['role'] == 'user' else f"[bold cyan]{AI_NAME}[/bold cyan]"
                content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                rprint(f"{role}: {content}")
        
        return conversation
    except Exception as e:
        rprint(f"\n[bold red]Error reading memory: {str(e)}[/bold red]")
        return []

def load_context_from_file(filename):
    """
    Load a custom context/prompt from a file
    """
    try:
        with open(filename, 'r') as f:
            return f.read().strip()
    except Exception as e:
        rprint(f"\n[bold red]Error loading context: {str(e)}[/bold red]")
        return DEFAULT_SYSTEM_PROMPT

def help():
    print("""
    \033[47m\033[30m ChatTUI Help \033[0m

    description,
        Welcome to ChatTUI, a command-line NLP based on ollama!

    Usage: chatui [options]

    Options:
    -help:      Display this help message
    -load:      Load conversation history from file
    -context:   Provede a file to read as context
          """)
    exit(1)

def run_chatbot(context_file=None):
    """Main chatbot function"""
    conversation = []
    
    # Load context/prompt
    system_prompt = load_context_from_file(context_file) if context_file else DEFAULT_SYSTEM_PROMPT
    conversation.append({
        'role': 'system',
        'content': system_prompt
    })
    
    # Check if there's a conversation file to load
    if len(sys.argv) > 1:
        if sys.argv[1] == '-help':
            help()
        elif sys.argv[1] == '-load':
            if len(sys.argv) < 3:
                print("\033[91mCHATUI:\033[0m You are attempting to load a file, please provide the approprate filename.\033[0m")
                exit(1)
            filename = sys.argv[2]
            rprint(f"\n[bold blue]Loading conversation from {filename}...[/bold blue]")
            loaded_conversation = load_conversation_from_file(filename)
            # Insert loaded conversation after system prompt
            if loaded_conversation:
                conversation.extend(loaded_conversation)
        else:
            print("\033[91mCHATUI:\033[0m Invalid option. Use -help for more information.\033[0m")
            exit(1)

    os.system("clear")
    while True:
        # Get user input
        try:
            user_input = input(f"\033[40m\033[97m\n {getpass.getuser()}: \033[0m ").strip()
            
            # Check for commands
            if user_input.lower() in ['quit', 'exit']:
                save = input("\nWould you like to save the conversation? (y/n): ").strip().lower()
                if save.startswith('y'):
                    save_conversation_to_file(conversation)
                rprint("\n[bold green]Goodbye![/bold green]")
                break
            
            # Check for memory reading command
            if user_input.lower().startswith('memory '):
                memory_file = user_input[7:].strip()
                read_memory(memory_file)
                continue
            
            # Add user message to conversation
            conversation.append({
                'role': 'user',
                'content': user_input
            })
            
        except KeyboardInterrupt:
            rprint("\n\n[bold yellow]Ctrl+C detected[/bold yellow]")
            save = input("\nWould you like to save the conversation? (y/n): ").strip().lower()
            if save.startswith('y'):
                save_conversation_to_file(conversation)
            rprint("\n[bold green]Goodbye![/bold green]")
            break
        
        try:
            # Get AI response
            bot_response = get_ai_response(conversation)
            
            # Display response with markdown
            print(f"\033[47m\033[90m\n {AI_NAME}: \033[0m")
            render_markdown(bot_response)
            
            # Add bot response to conversation history
            conversation.append({
                'role': 'assistant',
                'content': bot_response
            })
            
        except Exception as e:
            rprint(f"\n[bold red]Error:[/bold red] {str(e)}")
            rprint("[yellow]Please try again.[/yellow]")

if __name__ == "__main__":
    # You can specify a context file as an environment variable
    context_file = os.getenv('CHATUI_CONTEXT')
    run_chatbot(context_file)
