import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

print("Testing Gemini API with google-genai (LiveKit's library)...")
print(f"API Key found: {bool(os.getenv('GOOGLE_API_KEY'))}")
print(f"API Key (first 10 chars): {os.getenv('GOOGLE_API_KEY', 'NOT FOUND')[:10]}...")

async def test_gemini():
    try:
        from google import genai
        from google.genai import types
        
        api_key = os.getenv('GOOGLE_API_KEY')
        
        # Create client
        client = genai.Client(api_key=api_key)
        
        # Test with gemini-1.5-flash
        print("\n=== Testing gemini-1.5-flash ===")
        try:
            response = await client.aio.models.generate_content(
                model='gemini-1.5-flash',
                contents='Say hello in one word'
            )
            print(f"✓ SUCCESS! Response: {response.text}")
        except Exception as e:
            print(f"✗ FAILED with gemini-1.5-flash")
            print(f"Error: {type(e).__name__}: {str(e)}")
        
        # Test with gemini-2.0-flash-exp
        print("\n=== Testing gemini-2.0-flash-exp ===")
        try:
            response = await client.aio.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents='Say hello in one word'
            )
            print(f"✓ SUCCESS! Response: {response.text}")
        except Exception as e:
            print(f"✗ FAILED with gemini-2.0-flash-exp")
            print(f"Error: {type(e).__name__}: {str(e)}")
        
        # Try to list available models
        print("\n=== Checking available models ===")
        try:
            models = await client.aio.models.list()
            print("Available models:")
            for model in models.models[:10]:  # Show first 10
                print(f"  - {model.name}")
        except Exception as e:
            print(f"Could not list models: {e}")
            
    except ImportError as e:
        print(f"\n✗ Import Error: {e}")
        print("\nThe google-genai package is installed (LiveKit uses it)")
        print("But there might be a configuration issue.")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        traceback.print_exc()

# Run the async test
asyncio.run(test_gemini())

print("\n" + "="*50)
print("DIAGNOSIS:")
print("="*50)
print("If both models failed with '429 Too Many Requests':")
print("  → Your API key has NO quota (limit: 0)")
print("  → Solution: Create NEW key at https://aistudio.google.com/apikey")
print("  → OR: Enable billing at https://console.cloud.google.com/billing")
print("\nIf gemini-1.5-flash worked but gemini-2.0-flash-exp failed:")
print("  → Use gemini-1.5-flash in your agent")
print("\nIf BOTH worked:")
print("  → Your API key is fine! Problem is elsewhere")
print("="*50)