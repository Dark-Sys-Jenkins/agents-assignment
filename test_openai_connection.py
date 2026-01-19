import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found.")
        return

    print(f"Testing OpenAI connection with key: {api_key[:5]}...")
    
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        models = await client.models.list()
        print("Successfully listed models. Connection is good.")
        # print("First 5 models:", [m.id for m in models.data[:5]])
    except Exception as e:
        print(f"Error connecting to OpenAI: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai())
