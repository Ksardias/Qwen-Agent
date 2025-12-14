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
Privacy and security validation utilities for ensuring local-only operation.

This module helps users verify that their Qwen-Agent configuration will not
send data to external servers when using local LLM models.
"""

import os
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

from qwen_agent.log import logger
from qwen_agent.tools.base import BaseTool

# Tools that are known to make external API calls
EXTERNAL_TOOLS = {
    'web_search': {
        'service': 'Google Serper API',
        'env_var': 'SERPER_API_KEY',
        'description': 'Searches the web using external Google Serper API'
    },
    'image_search': {
        'service': 'SerpAPI',
        'env_var': 'SERPAPI_IMAGE_SEARCH_KEY',
        'description': 'Performs reverse image search using external SerpAPI'
    },
    'image_gen': {
        'service': 'Pollinations.ai',
        'env_var': None,
        'description': 'Generates images using external Pollinations.ai service'
    },
    'amap_weather': {
        'service': 'AMap Weather API',
        'env_var': 'AMAP_TOKEN',
        'description': 'Fetches weather data from external AMap API'
    },
}

# Model types that use external services
EXTERNAL_MODEL_TYPES = {
    'qwen_dashscope': {
        'service': 'Alibaba Cloud DashScope',
        'env_var': 'DASHSCOPE_API_KEY',
        'description': 'Cloud-based model service from Alibaba'
    },
    'azure': {
        'service': 'Microsoft Azure OpenAI',
        'env_var': 'AZURE_API_KEY',
        'description': 'Cloud-based model service from Microsoft Azure'
    },
}

# Local-only model types
LOCAL_MODEL_TYPES = {
    'transformers',
    'openvino',
}


def is_local_url(url: str) -> bool:
    """Check if a URL points to a local service."""
    if not url:
        return True
    
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        return True
    
    # Check for localhost variations
    local_hosts = {
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '::1',  # IPv6 localhost
    }
    
    if hostname.lower() in local_hosts:
        return True
    
    # Check for local network ranges (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    if hostname.startswith('192.168.') or hostname.startswith('10.'):
        return True
    
    # Check 172.16.0.0 - 172.31.255.255
    if hostname.startswith('172.'):
        try:
            second_octet = int(hostname.split('.')[1])
            if 16 <= second_octet <= 31:
                return True
        except (ValueError, IndexError):
            pass
    
    return False


def validate_llm_config(llm_cfg: Dict) -> List[str]:
    """
    Validate LLM configuration for privacy concerns.
    
    Args:
        llm_cfg: LLM configuration dictionary
        
    Returns:
        List of privacy issues found (empty list if no issues)
    """
    issues = []
    
    model_type = llm_cfg.get('model_type', '').lower()
    
    # Check for external model types
    if model_type in EXTERNAL_MODEL_TYPES:
        ext_info = EXTERNAL_MODEL_TYPES[model_type]
        issues.append(
            f"⚠️  LLM backend '{model_type}' uses external service: {ext_info['service']}. "
            f"{ext_info['description']}. "
            "For local-only operation, use 'transformers', 'openvino', or configure 'oai' type with local server."
        )
    
    # Check model_server URL
    model_server = llm_cfg.get('model_server') or llm_cfg.get('base_url') or llm_cfg.get('api_base')
    
    # Special case: dashscope string means external
    if model_server and isinstance(model_server, str):
        if model_server.lower() == 'dashscope':
            issues.append(
                "⚠️  model_server='dashscope' uses external Alibaba Cloud service. "
                "For local-only operation, set model_server to your local endpoint (e.g., 'http://localhost:8000/v1')."
            )
        elif not is_local_url(model_server):
            issues.append(
                f"⚠️  model_server='{model_server}' appears to be an external URL. "
                "For local-only operation, ensure model_server points to localhost or local network address "
                "(e.g., 'http://localhost:8000/v1', 'http://127.0.0.1:8000/v1')."
            )
    
    # If using oai type without explicit local server, warn
    if model_type == 'oai' and not model_server:
        # Check if it might be using OpenAI's actual API
        if os.getenv('OPENAI_API_KEY'):
            issues.append(
                "⚠️  Using 'oai' model type with OPENAI_API_KEY environment variable set. "
                "This will send data to external OpenAI API. "
                "For local-only operation, set 'model_server' to your local endpoint and unset OPENAI_API_KEY."
            )
    
    # Check for external API keys that might be used
    external_api_keys = {
        'DASHSCOPE_API_KEY': 'Alibaba Cloud DashScope',
        'OPENAI_API_KEY': 'OpenAI API',
        'AZURE_API_KEY': 'Microsoft Azure OpenAI',
    }
    
    for env_var, service in external_api_keys.items():
        if os.getenv(env_var) and not model_server:
            # Only warn if no local server is configured
            issues.append(
                f"ℹ️  Environment variable {env_var} is set ({service}). "
                f"Ensure 'model_server' is configured to point to local service if you want local-only operation."
            )
    
    return issues


def validate_tools_config(tools: List[Union[str, Dict, BaseTool]]) -> List[str]:
    """
    Validate tools configuration for privacy concerns.
    
    Args:
        tools: List of tools (can be tool names, configs, or objects)
        
    Returns:
        List of privacy issues found (empty list if no issues)
    """
    issues = []
    
    if not tools:
        return issues
    
    for tool in tools:
        tool_name = None
        
        if isinstance(tool, str):
            tool_name = tool
        elif isinstance(tool, dict):
            if 'mcpServers' in tool:
                # MCP configuration - might be local or external
                issues.append(
                    "ℹ️  MCP (Model Context Protocol) servers detected. "
                    "MCP servers can be local or external depending on the specific server. "
                    "Review each MCP server's configuration to ensure it's local-only if required. "
                    "Common local MCP servers: mcp-server-filesystem, mcp-server-memory. "
                    "Common external MCP servers: mcp-server-fetch (makes HTTP requests)."
                )
                continue
            tool_name = tool.get('name')
        elif isinstance(tool, BaseTool):
            tool_name = tool.name
        
        if tool_name and tool_name in EXTERNAL_TOOLS:
            ext_info = EXTERNAL_TOOLS[tool_name]
            env_var_msg = f" (requires {ext_info['env_var']})" if ext_info['env_var'] else ""
            issues.append(
                f"⚠️  Tool '{tool_name}' makes external API calls: {ext_info['description']}. "
                f"Service: {ext_info['service']}{env_var_msg}. "
                "For local-only operation, remove this tool from function_list."
            )
    
    return issues


def validate_privacy_config(
    llm_cfg: Optional[Dict] = None,
    tools: Optional[List[Union[str, Dict, BaseTool]]] = None,
    strict: bool = False
) -> List[str]:
    """
    Validate complete configuration for privacy and local-only operation.
    
    Args:
        llm_cfg: LLM configuration dictionary
        tools: List of tools configuration
        strict: If True, also check for environment variables of external services
        
    Returns:
        List of all privacy issues found (empty list if no issues)
    """
    all_issues = []
    
    # Validate LLM configuration
    if llm_cfg:
        all_issues.extend(validate_llm_config(llm_cfg))
    
    # Validate tools configuration
    if tools:
        all_issues.extend(validate_tools_config(tools))
    
    # In strict mode, check for any external API keys
    if strict:
        all_external_keys = {
            'DASHSCOPE_API_KEY': 'Alibaba Cloud DashScope',
            'OPENAI_API_KEY': 'OpenAI',
            'AZURE_API_KEY': 'Microsoft Azure OpenAI',
            'SERPER_API_KEY': 'Google Serper (web search)',
            'SERPAPI_IMAGE_SEARCH_KEY': 'SerpAPI (image search)',
            'AMAP_TOKEN': 'AMap Weather API',
        }
        
        found_keys = []
        for env_var, service in all_external_keys.items():
            if os.getenv(env_var):
                found_keys.append(f"{env_var} ({service})")
        
        if found_keys:
            all_issues.append(
                f"ℹ️  External API keys detected in environment (strict mode): {', '.join(found_keys)}. "
                "For guaranteed local-only operation, consider unsetting these environment variables."
            )
    
    return all_issues


def run_privacy_check(
    llm_cfg: Optional[Dict] = None,
    tools: Optional[List[Union[str, Dict, BaseTool]]] = None,
    strict: bool = False,
    verbose: bool = True
) -> bool:
    """
    Run privacy check and print results.
    
    Args:
        llm_cfg: LLM configuration dictionary
        tools: List of tools configuration
        strict: If True, perform strict validation including environment variables
        verbose: If True, print detailed information
        
    Returns:
        True if configuration is safe for local-only operation, False otherwise
    """
    issues = validate_privacy_config(llm_cfg, tools, strict=strict)
    
    if verbose:
        if not issues:
            msg = "✅ Privacy check passed - configuration appears to be local-only"
            logger.info(msg)
            print(msg)
            print("\nConfiguration summary:")
            if llm_cfg:
                model_type = llm_cfg.get('model_type', 'oai')
                model_server = llm_cfg.get('model_server') or llm_cfg.get('base_url') or 'not specified'
                print(f"  • LLM backend: {model_type}")
                print(f"  • Model server: {model_server}")
            if tools:
                print(f"  • Number of tools: {len(tools)}")
                tool_names = []
                for tool in tools:
                    if isinstance(tool, str):
                        tool_names.append(tool)
                    elif isinstance(tool, dict):
                        if 'name' in tool:
                            tool_names.append(tool['name'])
                        elif 'mcpServers' in tool:
                            tool_names.append('MCP servers')
                    elif isinstance(tool, BaseTool):
                        tool_names.append(tool.name)
                if tool_names:
                    print(f"  • Tools: {', '.join(tool_names)}")
            return True
        else:
            msg = f"⚠️  Privacy check found {len(issues)} issue(s)"
            logger.warning(msg)
            print(f"\n{msg}:\n")
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue}\n")
            
            print("\n" + "="*80)
            print("For local-only operation guidance, see: LOCAL_LLM_PRIVACY.md")
            print("="*80)
            return False
    else:
        return len(issues) == 0


def get_local_config_template(backend: str = 'vllm') -> Dict:
    """
    Get a template configuration for local-only operation.
    
    Args:
        backend: Backend type ('vllm', 'ollama', or 'transformers')
        
    Returns:
        Dictionary with recommended local-only configuration
    """
    templates = {
        'vllm': {
            'llm_cfg': {
                'model': 'Qwen/Qwen2.5-7B-Instruct',
                'model_server': 'http://localhost:8000/v1',
                'api_key': 'EMPTY',
            },
            'tools': ['code_interpreter', 'doc_parser'],
            'description': 'vLLM with OpenAI-compatible API (recommended for GPU)',
            'setup_command': 'python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000'
        },
        'ollama': {
            'llm_cfg': {
                'model': 'qwen2.5:7b',
                'model_server': 'http://localhost:11434/v1',
                'api_key': 'EMPTY',
            },
            'tools': ['code_interpreter', 'doc_parser'],
            'description': 'Ollama (recommended for CPU/small GPU)',
            'setup_command': 'ollama serve && ollama pull qwen2.5:7b'
        },
        'transformers': {
            'llm_cfg': {
                'model': 'Qwen/Qwen2.5-7B-Instruct',
                'model_type': 'transformers',
                'device': 'cuda',  # or 'cpu'
            },
            'tools': ['code_interpreter', 'doc_parser'],
            'description': 'Direct model loading with transformers',
            'setup_command': 'pip install transformers torch'
        },
    }
    
    if backend not in templates:
        raise ValueError(f"Unknown backend: {backend}. Choose from: {list(templates.keys())}")
    
    return templates[backend]


def print_local_config_guide():
    """Print a quick guide for local-only configuration."""
    print("\n" + "="*80)
    print("QWEN-AGENT LOCAL-ONLY CONFIGURATION GUIDE")
    print("="*80)
    print("\nTo ensure NO data is sent to external servers:\n")
    
    print("1. Use a local LLM backend:")
    print("   • vLLM (GPU): model_server='http://localhost:8000/v1'")
    print("   • Ollama (CPU): model_server='http://localhost:11434/v1'")
    print("   • Transformers: model_type='transformers'\n")
    
    print("2. Use only local tools:")
    print("   • ✅ Safe: code_interpreter, doc_parser, retrieval")
    print("   • ❌ Avoid: web_search, image_search, image_gen, amap_weather\n")
    
    print("3. Unset external API keys:")
    print("   unset DASHSCOPE_API_KEY OPENAI_API_KEY SERPER_API_KEY\n")
    
    print("4. Validate your configuration:")
    print("   from qwen_agent.utils.privacy_check import run_privacy_check")
    print("   run_privacy_check(llm_cfg, tools, strict=True)\n")
    
    print("For detailed guide, see: LOCAL_LLM_PRIVACY.md")
    print("="*80 + "\n")


if __name__ == '__main__':
    # Example usage and self-test
    print_local_config_guide()
    
    # Test case 1: Good local configuration
    print("\n--- Test Case 1: Local vLLM configuration ---")
    local_cfg = get_local_config_template('vllm')
    run_privacy_check(local_cfg['llm_cfg'], local_cfg['tools'], strict=True)
    
    # Test case 2: Bad external configuration
    print("\n--- Test Case 2: External DashScope configuration ---")
    external_cfg = {
        'model': 'qwen-max',
        'model_type': 'qwen_dashscope',
    }
    external_tools = ['web_search', 'image_gen']
    run_privacy_check(external_cfg, external_tools, strict=False)
    
    # Test case 3: Mixed configuration
    print("\n--- Test Case 3: Mixed configuration (local LLM + external tools) ---")
    mixed_cfg = {
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'model_server': 'http://localhost:8000/v1',
        'api_key': 'EMPTY',
    }
    mixed_tools = ['code_interpreter', 'web_search']
    run_privacy_check(mixed_cfg, mixed_tools, strict=False)
