import os
import asyncio
from dotenv import load_dotenv
from google.genai import Client, types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

async def main():
    client = Client(api_key=api_key)
    try:
        print("Testing gemini-2.0-flash-001 with system instruction ONLY...")
        # Simulate what the plugin does: system instruction set, but empty contents
        config = types.GenerateContentConfig(
            system_instruction=[types.Part(text="You are a helpful assistant.")]
        )
        
        # Passing empty list for contents
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=[], # Empty contents
            config=config
        )
        print("Success:", response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
