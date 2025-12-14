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
Tests for privacy_check utility.
"""

import os
import pytest
from qwen_agent.utils.privacy_check import (
    is_local_url,
    validate_llm_config,
    validate_tools_config,
    validate_privacy_config,
    get_local_config_template,
)


def test_is_local_url():
    """Test URL locality detection."""
    # Local URLs
    assert is_local_url('http://localhost:8000')
    assert is_local_url('http://127.0.0.1:8000')
    assert is_local_url('http://0.0.0.0:8000')
    assert is_local_url('http://192.168.1.100:8000')
    assert is_local_url('http://10.0.0.1:8000')
    assert is_local_url('http://172.16.0.1:8000')
    assert is_local_url('')
    assert is_local_url(None)

    # External URLs
    assert not is_local_url('https://api.openai.com')
    assert not is_local_url('https://dashscope.aliyuncs.com')
    assert not is_local_url('http://example.com')


def test_validate_llm_config_local():
    """Test validation of local LLM configurations."""
    # Valid local configuration - vLLM
    llm_cfg = {
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'model_server': 'http://localhost:8000/v1',
        'api_key': 'EMPTY',
    }
    issues = validate_llm_config(llm_cfg)
    assert len(issues) == 0
    
    # Valid local configuration - transformers
    llm_cfg = {
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'model_type': 'transformers',
    }
    issues = validate_llm_config(llm_cfg)
    assert len(issues) == 0


def test_validate_llm_config_external():
    """Test validation detects external LLM configurations."""
    # DashScope configuration (external)
    llm_cfg = {
        'model': 'qwen-max',
        'model_type': 'qwen_dashscope',
    }
    issues = validate_llm_config(llm_cfg)
    assert len(issues) > 0
    assert any('dashscope' in issue.lower() for issue in issues)
    
    # External URL
    llm_cfg = {
        'model': 'gpt-4',
        'model_server': 'https://api.openai.com/v1',
    }
    issues = validate_llm_config(llm_cfg)
    assert len(issues) > 0
    assert any('external' in issue.lower() for issue in issues)


def test_validate_tools_config_local():
    """Test validation of local tools."""
    tools = ['code_interpreter', 'doc_parser']
    issues = validate_tools_config(tools)
    assert len(issues) == 0


def test_validate_tools_config_external():
    """Test validation detects external tools."""
    # External tool - web_search
    tools = ['web_search']
    issues = validate_tools_config(tools)
    assert len(issues) > 0
    assert any('web_search' in issue for issue in issues)
    
    # Mixed tools
    tools = ['code_interpreter', 'image_gen', 'doc_parser']
    issues = validate_tools_config(tools)
    assert len(issues) > 0
    assert any('image_gen' in issue for issue in issues)
    
    # All external tools
    tools = ['web_search', 'image_search', 'image_gen', 'amap_weather']
    issues = validate_tools_config(tools)
    assert len(issues) == 4  # Should flag all 4 tools


def test_validate_privacy_config_complete():
    """Test complete privacy validation."""
    # Safe configuration
    llm_cfg = {
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'model_server': 'http://localhost:8000/v1',
    }
    tools = ['code_interpreter']
    issues = validate_privacy_config(llm_cfg, tools)
    assert len(issues) == 0
    
    # Unsafe configuration
    llm_cfg = {
        'model': 'qwen-max',
        'model_type': 'qwen_dashscope',
    }
    tools = ['web_search', 'code_interpreter']
    issues = validate_privacy_config(llm_cfg, tools)
    assert len(issues) >= 2  # LLM issue + tool issue


def test_get_local_config_template():
    """Test getting local configuration templates."""
    # vLLM template
    config = get_local_config_template('vllm')
    assert 'llm_cfg' in config
    assert 'tools' in config
    assert config['llm_cfg']['model_server'] == 'http://localhost:8000/v1'
    
    # Ollama template
    config = get_local_config_template('ollama')
    assert config['llm_cfg']['model_server'] == 'http://localhost:11434/v1'
    
    # Transformers template
    config = get_local_config_template('transformers')
    assert config['llm_cfg']['model_type'] == 'transformers'
    
    # Invalid backend
    with pytest.raises(ValueError):
        get_local_config_template('invalid_backend')


def test_mcp_detection():
    """Test MCP server detection in tools."""
    tools = [
        {
            'mcpServers': {
                'filesystem': {
                    'command': 'npx',
                    'args': ['-y', '@modelcontextprotocol/server-filesystem']
                }
            }
        }
    ]
    issues = validate_tools_config(tools)
    # Should have info about MCP
    assert len(issues) > 0
    assert any('MCP' in issue for issue in issues)


def test_dashscope_string_detection():
    """Test detection of 'dashscope' string as model_server."""
    llm_cfg = {
        'model': 'qwen-max',
        'model_server': 'dashscope',
    }
    issues = validate_llm_config(llm_cfg)
    assert len(issues) > 0
    assert any('dashscope' in issue.lower() for issue in issues)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
