import os
import asyncio
from dotenv import load_dotenv
from google.genai import Client

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

async def main():
    if not api_key:
        print("No API Key")
        return
    
    print(f"Using API Key: {api_key[:5]}...")
    client = Client(api_key=api_key)
    candidate_models = ["gemini-1.5-flash", "gemini-1.5-flash-001", "gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-2.0-flash-001"]
    
    for model in candidate_models:
        print(f"Testing {model}...")
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents="Hello"
            )
            print(f"Success with {model}:", response.text)
            return
        except Exception as e:
            print(f"Failed {model}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
