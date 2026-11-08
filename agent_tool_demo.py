import json
import os

os.environ["AGENT_LIBRARY_PATH"] = "knowledge_vault"

from library4agents import tools

def mock_llm_generate(messages):
    """
    A mock LLM that is hardcoded to respond to a specific user prompt by
    calling our tools, to demonstrate deterministically how the agent loop works.
    """
    last_msg = messages[-1]
    
    # 1. When user asks for a scraper, the LLM decides to search the library first.
    if last_msg["role"] == "user" and "scraper" in last_msg["content"].lower():
        print("[LLM Thought]: I need to build a scraper. Let me check the library for mapped territories first.")
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "search_expertise",
                        "arguments": json.dumps({"query": "scraping"})
                    }
                }
            ]
        }
        
    # 2. When the tool returns the data, the LLM reads it and writes the code.
    elif last_msg["role"] == "tool" and last_msg["tool_call_id"] == "call_abc123":
        knowledge = json.loads(last_msg["content"])
        print("[LLM Thought]: I see that parsing HTML with regex is a dead end. I will use BeautifulSoup for static HTML as recommended by Agent_A.")
        
        response = "Based on the mapped territory from Agent_A, I will use BeautifulSoup instead of Regex. Here is the code..."
        return {
            "role": "assistant",
            "content": response
        }

def run_agent_loop():
    print("--- Starting Agent Loop ---")
    
    # Initialize the conversation
    messages = [
        {"role": "system", "content": "You are a helpful coding agent. You have access to the local agent library via tools."},
        {"role": "user", "content": "Please write a Python web scraper for me."}
    ]
    
    print(f"\nUser: {messages[-1]['content']}")
    
    # First turn: LLM decides to call a tool
    response_message = mock_llm_generate(messages)
    messages.append(response_message)
    
    # Check if LLM wanted to call tools
    if response_message.get("tool_calls"):
        for tool_call in response_message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])
            
            print(f"\n[Tool Execution]: LLM called '{func_name}' with args {func_args}")
            
            # Execute the actual tool function from our library!
            if func_name == "search_expertise":
                result = tools.search_expertise(**func_args)
            elif func_name == "contribute_expertise":
                result = tools.contribute_expertise(**func_args)
            else:
                result = "Unknown function"
                
            print(f"[Tool Result]: Found {len(result)} territories mapped in the library.")
            
            # Append the tool result to the conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": func_name,
                "content": json.dumps(result)
            })
            
        # Second turn: LLM uses the tool results to answer the user
        final_response = mock_llm_generate(messages)
        messages.append(final_response)
        
        print(f"\nAgent: {final_response['content']}")

if __name__ == "__main__":
    run_agent_loop()
