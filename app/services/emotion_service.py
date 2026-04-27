import os
import logging
import httpx
from typing import List

logger = logging.getLogger(__name__)

EMOTION_MODEL_HF_KEY = os.getenv("EMOTION_MODEL_HF_KEY")
HF_API_URL = "https://api-inference.huggingface.co/models/SamLowe/roberta-base-go_emotions"

async def detect_emotions(text: str) -> List[str]:
    """
    Detect emotions using a Hugging Face model.
    """
    print(f"--- CALLING HF EMOTION API for: {text[:50]}... ---")
    if not EMOTION_MODEL_HF_KEY:
        print("HF KEY MISSING")
        logger.warning("EMOTION_MODEL_HF_KEY not found. Skipping HF emotion detection.")
        return []

    headers = {"Authorization": f"Bearer {EMOTION_MODEL_HF_KEY}"}
    payload = {"inputs": text}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(HF_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                # The model returns a list of lists: [[{"label": "sadness", "score": 0.9}, ...]]
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    emotions = data[0]
                    # Sort by score descending and pick top 2 if score > 0.1
                    top_emotions = [e["label"] for e in emotions if e.get("score", 0) > 0.1][:2]
                    return top_emotions
            elif response.status_code == 503:
                # Model is loading
                logger.info("HF Emotion model is loading (503). Falling back to Gemini.")
            else:
                logger.error(f"HF Emotion API failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"HF Emotion API exception: {e}")
        
    return []
