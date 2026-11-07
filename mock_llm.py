class MockChoice:
    def __init__(self, content, tool_calls=None):
        self.message = type('obj',(object,),{'content':content,'tool_calls':tool_calls or []})()

class MockResponse:
    def __init__(self, content):
        self.choices=[MockChoice(content)]
        self.usage={'total_tokens':100}

def mocked_chat_api(messages, tools=None, model="mock"):
    last=messages[-1]['content'].lower() if isinstance(messages[-1], dict) else str(messages[-1]).lower()
    if '45' in last or 'late' in last or 'delayed' in last:
        return MockResponse("As per Refund Policy, if delivery is delayed more than 45 minutes, delivery fee is waived.")
    if 'perishable' in last:
        return MockResponse("As per Refund Policy, perishable items refund within 2 hours of delivery.")
    if 'cod' in last:
        return MockResponse("As per Payment Policy, Cash on Delivery is available in all supported cities.")
    if '199' in last or 'below' in last:
        return MockResponse("As per Refund Policy, no refund on orders below INR 199.")
    return MockResponse("As per policy, check relevant policy document.")

def mock_llm(prompt, tools=None):
    return mocked_chat_api([{'content':prompt}])
