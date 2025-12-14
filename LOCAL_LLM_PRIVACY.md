# Local LLM Privacy Configuration Guide

This guide explains how to configure Qwen-Agent to ensure **no data is sent to external servers** when using a local LLM model.

## Overview

Qwen-Agent can make external network calls through two main channels:
1. **LLM Model Backend** - The language model service itself
2. **Tools** - Various tools that may call external APIs

To ensure complete privacy with a local LLM setup, you must properly configure both.

## External Service Dependencies

### LLM Backends

| Backend Type | Model Type | Privacy Status |
|--------------|------------|----------------|
| DashScope (Alibaba Cloud) | `qwen_dashscope` | ⚠️ **EXTERNAL** - Sends data to Alibaba Cloud |
| OpenAI API | `oai` | ⚠️ **EXTERNAL by default** - Can be local if configured to local endpoint |
| Azure OpenAI | `azure` | ⚠️ **EXTERNAL** - Sends data to Microsoft Azure |
| Transformers (Local) | `transformers` | ✅ **LOCAL** - No external calls |
| OpenVINO (Local) | `openvino` | ✅ **LOCAL** - No external calls |
| vLLM/Ollama (via OpenAI API) | `oai` with local server | ✅ **LOCAL** - If configured correctly |

### Tools with External Service Calls

| Tool | External Service | Required Environment Variable |
|------|------------------|------------------------------|
| `web_search` | Google Serper API | `SERPER_API_KEY` |
| `image_search` | SerpAPI | `SERPAPI_IMAGE_SEARCH_KEY` |
| `image_gen` | Pollinations.ai | None (always external) |
| `amap_weather` | AMap Weather API | `AMAP_TOKEN` |
| MCP tools (various) | Depends on MCP server | Varies |

### Tools that are Local/Safe

| Tool | Description |
|------|-------------|
| `code_interpreter` | Local code execution (Python) |
| `doc_parser` | Local document parsing |
| `simple_doc_parser` | Local simple document parsing |
| `retrieval` | Local vector search/RAG |

## Recommended Local-Only Configuration

### Option 1: Using vLLM (Recommended for GPU)

```python
from qwen_agent.agents import Assistant

# Configure local vLLM endpoint
llm_cfg = {
    'model': 'Qwen/Qwen2.5-7B-Instruct',
    'model_server': 'http://localhost:8000/v1',  # Local vLLM server
    'api_key': 'EMPTY',  # No real API key needed for local
}

# Only use local tools
tools = [
    'code_interpreter',  # Safe: executes Python locally
    'doc_parser',        # Safe: parses documents locally
]

# Create agent with local-only configuration
bot = Assistant(
    llm=llm_cfg,
    function_list=tools,
)
```

**Start vLLM server locally:**
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

### Option 2: Using Ollama (Recommended for CPU/Small GPU)

```python
from qwen_agent.agents import Assistant

# Configure local Ollama endpoint
llm_cfg = {
    'model': 'qwen2.5:7b',
    'model_server': 'http://localhost:11434/v1',  # Local Ollama server
    'api_key': 'EMPTY',
}

# Only use local tools
tools = ['code_interpreter', 'doc_parser']

bot = Assistant(llm=llm_cfg, function_list=tools)
```

**Start Ollama:**
```bash
ollama serve
ollama pull qwen2.5:7b
```

### Option 3: Using Transformers (Local Model Loading)

```python
from qwen_agent.agents import Assistant

# Load model directly with transformers
llm_cfg = {
    'model': 'Qwen/Qwen2.5-7B-Instruct',
    'model_type': 'transformers',  # Local model loading
    'device': 'cuda',  # or 'cpu'
}

tools = ['code_interpreter', 'doc_parser']

bot = Assistant(llm=llm_cfg, function_list=tools)
```

## Configuration Validation

Qwen-Agent provides a helper function to validate your configuration for privacy:

```python
from qwen_agent.utils.privacy_check import validate_privacy_config

# Validate your configuration
llm_cfg = {
    'model': 'Qwen/Qwen2.5-7B-Instruct',
    'model_server': 'http://localhost:8000/v1',
    'api_key': 'EMPTY',
}

tools = ['code_interpreter', 'web_search']  # web_search requires external API!

# This will warn about external dependencies
issues = validate_privacy_config(llm_cfg, tools)
if issues:
    print("⚠️  Privacy Configuration Issues:")
    for issue in issues:
        print(f"  - {issue}")
```

## What to Avoid for Local-Only Setup

### ❌ Do NOT use these configurations:

1. **DashScope backend:**
```python
# ❌ SENDS DATA TO EXTERNAL SERVER
llm_cfg = {
    'model': 'qwen-max',
    'model_type': 'qwen_dashscope',
}
```

2. **External API tools:**
```python
# ❌ THESE TOOLS CALL EXTERNAL APIS
tools = [
    'web_search',      # Calls Google Serper API
    'image_search',    # Calls SerpAPI
    'image_gen',       # Calls Pollinations.ai
    'amap_weather',    # Calls AMap API
]
```

3. **External OpenAI API:**
```python
# ❌ SENDS DATA TO OPENAI
llm_cfg = {
    'model': 'gpt-4',
    'api_key': 'sk-...',  # Real OpenAI API key
}
```

## Security Best Practices

1. **Always validate your configuration** before processing sensitive data
2. **Review tool list** - ensure no external API tools are included
3. **Check environment variables** - unset external API keys if not needed:
   ```bash
   unset DASHSCOPE_API_KEY
   unset OPENAI_API_KEY
   unset SERPER_API_KEY
   unset SERPAPI_IMAGE_SEARCH_KEY
   unset AMAP_TOKEN
   ```
4. **Use local model server** - prefer vLLM or Ollama for production
5. **Network isolation** - run in an isolated network environment if handling highly sensitive data
6. **Monitor network traffic** - use tools like `tcpdump` or `wireshark` to verify no external calls

## Verifying Local-Only Operation

### Method 1: Network Monitoring
```bash
# Monitor network connections while running your agent
sudo tcpdump -i any -n 'tcp port not 22' | grep -v '127.0.0.1\|localhost'
```

### Method 2: Firewall Rules
```bash
# Block all external network access (Linux)
sudo iptables -A OUTPUT -d 127.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -d 192.168.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 10.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -j REJECT
```

### Method 3: Use the Privacy Check Tool
```python
from qwen_agent.utils.privacy_check import run_privacy_check

# Run comprehensive privacy check
run_privacy_check(llm_cfg, tools, verbose=True)
```

## Complete Local-Only Example

```python
#!/usr/bin/env python3
"""
Complete example of a privacy-focused local-only Qwen-Agent setup.
This configuration ensures NO data is sent to external servers.
"""
import os
from qwen_agent.agents import Assistant
from qwen_agent.utils.privacy_check import validate_privacy_config

# Ensure no external API keys are set
for key in ['DASHSCOPE_API_KEY', 'OPENAI_API_KEY', 'SERPER_API_KEY', 
            'SERPAPI_IMAGE_SEARCH_KEY', 'AMAP_TOKEN']:
    if key in os.environ:
        print(f"⚠️  Warning: {key} is set. Removing to ensure privacy.")
        del os.environ[key]

# Configure local LLM
llm_cfg = {
    'model': 'Qwen/Qwen2.5-7B-Instruct',
    'model_server': 'http://localhost:8000/v1',  # Local vLLM server
    'api_key': 'EMPTY',
}

# Only use local tools
tools = [
    'code_interpreter',  # Local Python execution
    'doc_parser',        # Local document parsing
]

# Validate configuration for privacy
issues = validate_privacy_config(llm_cfg, tools)
if issues:
    print("❌ Privacy configuration has issues:")
    for issue in issues:
        print(f"   {issue}")
    exit(1)

print("✅ Privacy configuration validated - no external services will be used")

# Create the agent
bot = Assistant(
    llm=llm_cfg,
    function_list=tools,
    system_message="You are a helpful AI assistant running locally."
)

# Use the agent
messages = []
while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ['exit', 'quit']:
        break
    
    messages.append({'role': 'user', 'content': user_input})
    
    response_text = ''
    for response in bot.run(messages):
        # Get the last message
        if response:
            response_text = response[-1].get('content', '')
    
    print(f"Bot: {response_text}")
    messages.extend(response)
```

## FAQ

### Q: How do I know if my setup is truly local-only?

A: Use the provided `validate_privacy_config()` function and monitor network traffic as described above. Also check that your `model_server` points to `localhost` or `127.0.0.1`.

### Q: Can I use RAG (Retrieval Augmented Generation) locally?

A: Yes! The `retrieval` tool works locally. You'll need to use local embeddings models as well.

### Q: What about MCP (Model Context Protocol) servers?

A: MCP servers can be local or external depending on the specific server. Review each MCP server's documentation. Many MCP servers like `mcp-server-filesystem` and `mcp-server-memory` are local-only.

### Q: Is the code interpreter safe to use?

A: The code interpreter executes Python code locally in your environment. It's "private" in terms of network access, but be aware it's not sandboxed and can access your filesystem. See the disclaimer in the README.

## Summary Checklist

Before processing sensitive data with Qwen-Agent:

- [ ] Using local LLM backend (vLLM, Ollama, or transformers)
- [ ] `model_server` points to localhost (if using OpenAI-compatible API)
- [ ] No external API tools in function_list (`web_search`, `image_search`, etc.)
- [ ] External API keys unset or removed from environment
- [ ] Configuration validated with `validate_privacy_config()`
- [ ] Network monitoring confirms no external connections (optional but recommended)

## Support

For questions about privacy and local deployment:
- Review this document carefully
- Check the [main README](README.md) for model deployment instructions
- Open an issue on GitHub if you discover any privacy concerns

---

**Last Updated:** 2025-12-14
