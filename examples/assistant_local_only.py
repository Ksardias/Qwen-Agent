#!/usr/bin/env python3
# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Example: Privacy-focused local-only Qwen-Agent setup.

This example demonstrates how to configure Qwen-Agent to ensure
NO data is sent to external servers when using a local LLM.

Requirements:
- Local LLM server running (vLLM, Ollama, or similar)
- No external API keys needed

For vLLM setup:
    python -m vllm.entrypoints.openai.api_server \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --host 0.0.0.0 \\
        --port 8000

For Ollama setup:
    ollama serve
    ollama pull qwen2.5:7b
"""

import os
import sys
import traceback
import argparse
from qwen_agent.agents import Assistant
from qwen_agent.utils.privacy_check import (
    run_privacy_check,
    get_local_config_template,
    print_local_config_guide,
)


def clean_external_api_keys():
    """Remove external API keys from environment to ensure privacy."""
    external_keys = [
        'DASHSCOPE_API_KEY',
        'OPENAI_API_KEY',
        'AZURE_API_KEY',
        'SERPER_API_KEY',
        'SERPAPI_IMAGE_SEARCH_KEY',
        'AMAP_TOKEN',
    ]
    
    removed = []
    for key in external_keys:
        if key in os.environ:
            del os.environ[key]
            removed.append(key)
    
    if removed:
        print(f"🧹 Cleaned external API keys from environment: {', '.join(removed)}")
    
    return removed


def setup_local_agent(backend: str = 'vllm'):
    """
    Set up a local-only agent with privacy validation.
    
    Args:
        backend: Backend type ('vllm', 'ollama', or 'transformers')
    
    Returns:
        Configured Assistant agent
    """
    # Get recommended local configuration
    config = get_local_config_template(backend)
    
    print(f"\n📝 Using {backend} backend:")
    print(f"   {config['description']}")
    print(f"\n🔧 Setup command: {config['setup_command']}\n")
    
    llm_cfg = config['llm_cfg']
    tools = config['tools']
    
    # Validate configuration for privacy
    print("🔍 Running privacy check...")
    is_safe = run_privacy_check(llm_cfg, tools, strict=True, verbose=True)
    
    if not is_safe:
        print("\n❌ Configuration has privacy concerns!")
        print("Please review the issues above before proceeding.")
        response = input("\nDo you want to continue anyway? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Exiting.")
            sys.exit(1)
    
    # Create the agent
    print("\n🤖 Creating local agent...")
    bot = Assistant(
        llm=llm_cfg,
        function_list=tools,
        system_message="You are a helpful AI assistant running locally with privacy protection."
    )
    
    print("✅ Local agent created successfully!\n")
    return bot


def interactive_chat(bot):
    """Run an interactive chat session with the agent."""
    print("="*80)
    print("INTERACTIVE CHAT (Privacy-Protected)")
    print("="*80)
    print("Type 'exit' or 'quit' to end the conversation")
    print("Type 'help' for available commands")
    print("="*80 + "\n")
    
    messages = []
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'help':
                print("\nAvailable commands:")
                print("  • exit/quit - End the conversation")
                print("  • help - Show this help message")
                print("  • Any other text - Chat with the AI\n")
                continue
            
            # Add user message
            messages.append({'role': 'user', 'content': user_input})
            
            # Get response from agent
            print("\nAssistant: ", end='', flush=True)
            response_text = ''
            last_len = 0
            
            for response in bot.run(messages):
                if response and len(response) > 0:
                    # Get the content from the last message
                    last_msg = response[-1]
                    if isinstance(last_msg, dict):
                        content = last_msg.get('content', '')
                    else:
                        content = getattr(last_msg, 'content', '')
                    
                    if content and len(content) > last_len:
                        # Print only new content (streaming effect)
                        print(content[last_len:], end='', flush=True)
                        last_len = len(content)
                        response_text = content
            
            print("\n")  # New line after response
            
            # Add response to messages
            messages.extend(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            traceback.print_exc()


def demo_local_assistant():
    """
    Demo function showing various ways to configure local-only assistant.
    """
    print("\n" + "="*80)
    print("QWEN-AGENT LOCAL-ONLY DEMO")
    print("="*80)
    
    # Clean external API keys
    print("\n1. Cleaning external API keys...")
    clean_external_api_keys()
    
    # Show configuration guide
    print("\n2. Configuration guide:")
    print_local_config_guide()
    
    # Ask user which backend to use
    print("\n3. Choose your local LLM backend:")
    print("   1. vLLM (recommended for GPU)")
    print("   2. Ollama (recommended for CPU/small GPU)")
    print("   3. Transformers (direct model loading)")
    
    backend_map = {
        '1': 'vllm',
        '2': 'ollama',
        '3': 'transformers',
    }
    
    choice = input("\nEnter your choice (1-3, default=1): ").strip() or '1'
    backend = backend_map.get(choice, 'vllm')
    
    # Set up local agent
    try:
        bot = setup_local_agent(backend)
        
        # Start interactive chat
        input("\n📍 Press Enter to start chatting (or Ctrl+C to exit)...")
        interactive_chat(bot)
        
    except Exception as e:
        print(f"\n❌ Error setting up agent: {e}")
        traceback.print_exc()
        print("\nPlease ensure your local LLM server is running.")
        print("See the setup command printed above for instructions.")
        sys.exit(1)


def example_programmatic_usage():
    """
    Example of programmatic usage with privacy validation.
    """
    print("\n" + "="*80)
    print("PROGRAMMATIC USAGE EXAMPLE")
    print("="*80 + "\n")
    
    # Clean external API keys
    clean_external_api_keys()
    
    # Configure local LLM
    llm_cfg = {
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'model_server': 'http://localhost:8000/v1',
        'api_key': 'EMPTY',
    }
    
    # Configure local tools only
    tools = [
        'code_interpreter',  # Local Python execution
        'doc_parser',        # Local document parsing
    ]
    
    # Validate configuration
    print("🔍 Validating privacy configuration...")
    is_safe = run_privacy_check(llm_cfg, tools, strict=True)
    
    if not is_safe:
        print("❌ Configuration is not safe for local-only operation!")
        return
    
    print("\n✅ Configuration validated - safe for local-only operation\n")
    
    # Create agent
    print("🤖 Creating agent...")
    bot = Assistant(
        llm=llm_cfg,
        function_list=tools,
        system_message="You are a helpful AI assistant."
    )
    
    # Example conversation
    messages = [
        {'role': 'user', 'content': 'Hello! Can you help me write a Python function to calculate factorial?'}
    ]
    
    print("📝 Example query: " + messages[0]['content'])
    print("\n🤖 Agent response:")
    
    for response in bot.run(messages):
        if response:
            last_msg = response[-1]
            if isinstance(last_msg, dict):
                print(last_msg.get('content', ''))
            else:
                print(getattr(last_msg, 'content', ''))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Privacy-focused local-only Qwen-Agent example',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive demo (choose backend interactively)
  python examples/assistant_local_only.py
  
  # Use specific backend
  python examples/assistant_local_only.py --backend vllm
  python examples/assistant_local_only.py --backend ollama
  
  # Programmatic usage example
  python examples/assistant_local_only.py --mode programmatic
  
  # Just show the configuration guide
  python examples/assistant_local_only.py --mode guide
        """
    )
    
    parser.add_argument(
        '--backend',
        choices=['vllm', 'ollama', 'transformers'],
        default=None,
        help='LLM backend to use (default: interactive selection)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['interactive', 'programmatic', 'guide'],
        default='interactive',
        help='Run mode (default: interactive)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'guide':
        print_local_config_guide()
    elif args.mode == 'programmatic':
        example_programmatic_usage()
    else:  # interactive
        if args.backend:
            clean_external_api_keys()
            bot = setup_local_agent(args.backend)
            interactive_chat(bot)
        else:
            demo_local_assistant()
