from backend.llm_client import test_connection, call_llm_json
print('Connection:', test_connection())
print('Test call:', call_llm_json('Return JSON: {"action": "test", "reasoning": "hello", "confidence": 0.9}'))