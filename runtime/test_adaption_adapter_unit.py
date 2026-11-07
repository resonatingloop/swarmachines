"""
Unit tests for the Adaption adapter with mocked SDK.

These tests validate the adapter's interface and error handling
without requiring live API access. They can run in CI without
ADAPTION_API_KEY set.

The SDK is mocked to avoid requiring actual API access. Tests
verify the adapter's wrapper logic, not the SDK itself.

Usage:
    python runtime/test_adaption_adapter_unit.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent))


def test_adapter_response_structure():
    """
    Test that adapter returns correctly structured response when SDK is mocked.
    """
    # Mock the SDK response
    mock_response = Mock()
    mock_response.output_text = "test response"
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5
    mock_response.model = "test-model"
    
    mock_client = Mock()
    mock_client.responses.create.return_value = mock_response
    
    # Create a mock Adaption class that returns our mock client
    mock_adaption_class = Mock(return_value=mock_client)
    
    # Patch the adaption module itself
    with patch.dict('sys.modules', {'adaption': Mock(Adaption=mock_adaption_class)}):
        # Now import after the patch is in place
        from adaption_adapter import AdaptionAdapter
        adapter = AdaptionAdapter()
        
        response = adapter.simple_prompt(
            model="test-model",
            prompt="test prompt",
        )
        
        # Verify response structure
        assert response.output_text == "test response", f"Expected 'test response', got {response.output_text}"
        assert response.usage.input_tokens == 10, f"Expected 10 input tokens, got {response.usage.input_tokens}"
        assert response.usage.output_tokens == 5, f"Expected 5 output tokens, got {response.usage.output_tokens}"
        assert response.usage.total_tokens == 15, f"Expected 15 total tokens, got {response.usage.total_tokens}"
        assert response.model == "test-model", f"Expected 'test-model', got {response.model}"
        assert response.latency_ms >= 0, f"Expected non-negative latency, got {response.latency_ms}"
        
        return True, "OK: response structure validated"


def test_adapter_chat_interface():
    """
    Test that adapter.chat() accepts messages format correctly.
    """
    mock_response = Mock()
    mock_response.output_text = "chat response"
    mock_response.usage.input_tokens = 20
    mock_response.usage.output_tokens = 10
    mock_response.model = "test-model"
    
    mock_client = Mock()
    mock_client.responses.create.return_value = mock_response
    
    mock_adaption_class = Mock(return_value=mock_client)
    
    with patch.dict('sys.modules', {'adaption': Mock(Adaption=mock_adaption_class)}):
        from adaption_adapter import AdaptionAdapter
        adapter = AdaptionAdapter()
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        
        adapter.chat(
            model="test-model",
            messages=messages,
        )
        
        # Verify the SDK was called with correct parameters
        mock_client.responses.create.assert_called_once()
        call_args = mock_client.responses.create.call_args
        assert call_args[1]['model'] == "test-model", f"Expected model 'test-model', got {call_args[1]['model']}"
        assert call_args[1]['input'] == messages, f"Expected messages {messages}, got {call_args[1]['input']}"
        
        return True, "OK: chat interface validated"


def test_adapter_uses_input_parameter():
    """
    Test that adapter uses 'input' parameter (not 'messages') for Adaption API.
    
    This validates the fix for the input-vs-messages API mismatch.
    """
    mock_response = Mock()
    mock_response.output_text = "response"
    mock_response.usage.input_tokens = 5
    mock_response.usage.output_tokens = 5
    mock_response.model = "test-model"
    
    mock_client = Mock()
    mock_client.responses.create.return_value = mock_response
    
    mock_adaption_class = Mock(return_value=mock_client)
    
    with patch.dict('sys.modules', {'adaption': Mock(Adaption=mock_adaption_class)}):
        from adaption_adapter import AdaptionAdapter
        adapter = AdaptionAdapter()
        
        messages = [{"role": "user", "content": "test"}]
        adapter.chat(model="test-model", messages=messages)
        
        # Verify 'input' parameter is used (not 'messages')
        call_args = mock_client.responses.create.call_args
        assert 'input' in call_args[1], "Expected 'input' parameter in API call"
        assert 'messages' not in call_args[1], "Should not use 'messages' parameter"
        
        return True, "OK: uses 'input' parameter (not 'messages')"


def test_lazy_import_defers_sdk_dependency():
    """
    Test that the adapter defers SDK import until instantiation.
    
    This validates that the module can be imported without the SDK present,
    and only fails when actually instantiating the adapter without SDK.
    """
    # The module file exists and is readable
    adapter_path = Path(__file__).parent / "adaption_adapter.py"
    assert adapter_path.exists(), "adaption_adapter.py should exist"
    
    # The module uses lazy import (Adaption imported inside __init__)
    # Verify by checking the source contains the lazy import pattern
    source = adapter_path.read_text()
    assert "from adaption import Adaption" in source, "Should import Adaption"
    
    # Check that the import is inside a method (lazy), not at module level
    lines = source.split('\n')
    module_level_imports = [i for i, line in enumerate(lines) 
                           if line.strip().startswith('from adaption import') and i < 30]
    
    # There should be no module-level adaption imports (all should be lazy inside methods)
    # The lazy import is inside __init__ which is after line 30
    assert len(module_level_imports) == 0, "Adaption import should be lazy (inside method), not at module level"
    
    return True, "OK: lazy import pattern verified"


def run_tests():
    """Run all unit tests and report results."""
    tests = [
        ("adapter_response_structure", test_adapter_response_structure),
        ("adapter_chat_interface", test_adapter_chat_interface),
        ("adapter_uses_input_parameter", test_adapter_uses_input_parameter),
        ("lazy_import_defers_sdk_dependency", test_lazy_import_defers_sdk_dependency),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            success, message = test_fn()
            if success:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"
        except Exception as e:  # noqa: BLE001 - Test runner catches all test failures for reporting
            failed += 1
            success = False
            status = "ERROR"
            message = f"Exception: {e}"
        
        results.append({
            "test": name,
            "status": status,
            "message": message,
        })
        print(f"{status}: {name} - {message}")
    
    return {
        "passed": passed,
        "failed": failed,
        "total": len(tests),
        "results": results,
    }


if __name__ == "__main__":
    import json
    
    result = run_tests()
    print(f"\nResults: {result['passed']}/{result['total']} passed")
    
    if result['failed'] > 0:
        print(json.dumps(result, indent=2))
        sys.exit(1)
    else:
        sys.exit(0)
