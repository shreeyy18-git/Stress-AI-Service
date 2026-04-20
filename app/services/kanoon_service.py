import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Load API key from environment
INDIAN_KANOON_API_KEY = os.getenv("INDIAN_KANOON_API_KEY")
KANOON_API_URL = "https://api.indiankanoon.org/search/"

async def search_legal_context(query: str) -> str:
    """
    Search Indian Kanoon for laws (Central Acts/Rules) matching the query.
    Filters: doctypes=laws, sortby=mostrecent
    """
    if not INDIAN_KANOON_API_KEY:
        logger.warning("INDIAN_KANOON_API_KEY not found in environment. Skipping search.")
        return ""

    headers = {
        "Authorization": f"Token {INDIAN_KANOON_API_KEY}",
        "Accept": "application/json"
    }
    
    # We add filters to the query itself as per Indian Kanoon documentation for formInput
    # Parameters: doctypes:laws, sortby:mostrecent
    params = {
        "formInput": query,
        "doctypes": "laws",
        "sortby": "mostrecent"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(KANOON_API_URL, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.error("Indian Kanoon API error: %s | %s", response.status_code, response.text)
                return ""

            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return "No specific laws found for this query."

            # Format top 3 results into a concise snippet
            formatted_results = []
            for doc in results[:3]:
                title = doc.get("title", "Unknown Act")
                snippet = doc.get("snippet", "No description available.").replace("<b>", "").replace("</b>", "")
                formatted_results.append(f"Act Name: {title}\nSummary: {snippet}")

            return "\n\n".join(formatted_results)

    except Exception as e:
        logger.error("Exception during Indian Kanoon search: %s", e)
        return ""
