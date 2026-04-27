import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

INDIAN_KANOON_API_KEY = os.getenv("INDIAN_KANOON_API_KEY")
KANOON_API_URL = "https://api.indiankanoon.org/search/"

async def test_kanoon_direct():
    print(f"--- TESTING INDIAN KANOON API KEY: {INDIAN_KANOON_API_KEY[:5]}...{INDIAN_KANOON_API_KEY[-5:] if INDIAN_KANOON_API_KEY else 'NONE'} ---")
    
    if not INDIAN_KANOON_API_KEY:
        print("ERROR: INDIAN_KANOON_API_KEY is not set in .env")
        return

    headers = {
        "Authorization": f"Token {INDIAN_KANOON_API_KEY}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    params = {
        "formInput": "stalking",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(KANOON_API_URL, data=params, headers=headers)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"DEBUG: Full Response Data: {json.dumps(data, indent=2)[:500]}...")
                results = data.get("results", [])
                print(f"SUCCESS: Found {len(results)} results.")
                if results:
                    print("\nTop Result Example:")
                    print(f"Title: {results[0].get('title')}")
                    print(f"Snippet: {results[0].get('snippet')[:100]}...")
                else:
                    print("No results found, but API call was successful.")
            else:
                print(f"FAILED: {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_kanoon_direct())
