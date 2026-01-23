import sys
import os

# Set up the same path structure as the agent
current_dir = os.path.abspath(os.getcwd())
sys.path.insert(0, os.path.join(current_dir, "livekit-agents"))

try:
    from livekit.agents import llm
    print(f"LLM File: {llm.__file__}")
    
    from livekit.agents.llm.tool_context import ToolContext
    print(f"ToolContext File: {ToolContext.__module__}")
    
    ctx = ToolContext([])
    print(f"Has parse_function_tools: {hasattr(ctx, 'parse_function_tools')}")
    if hasattr(ctx, 'parse_function_tools'):
         print("SUCCESS: parse_function_tools found!")
    else:
         print("FAILURE: parse_function_tools NOT found!")
         print(f"Dir of ctx: {dir(ctx)}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
