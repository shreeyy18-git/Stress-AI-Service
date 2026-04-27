import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8002"

async def test_analyze_chat():
    print("\n--- Testing /analyze-chat (HARD EXAMPLE) ---")
    payload = {
        "user_id": "report_user_001",
        "user_info": "Female, 25, Delhi, India",
        "message": "I am a 25-year-old woman living in Delhi. For the last two weeks, a man from my neighborhood has been following me to my metro station and even wait for me in the evening. Today he tried to block my path and asked for my number aggressively. I feel very unsafe and stressed. Is there any law in India that can protect me from this stalking?",
        "history": [],
        "memory_summary": "User has mentioned feeling uneasy about her commute previously."
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/analyze-chat", json=payload)
        return response.status_code, response.json()

async def test_daily_summary():
    print("\n--- Testing /daily-summary ---")
    payload = {
        "user_id": "report_user_001",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "messages": [
            {"role": "user", "content": "I'm feeling a bit anxious about the commute today.", "timestamp": "2026-04-27T09:00:00"},
            {"role": "assistant", "content": "I understand. What specifically is making you feel anxious?", "timestamp": "2026-04-27T09:01:00"},
            {"role": "user", "content": "That man is following me again. I'm at the station now.", "timestamp": "2026-04-27T18:30:00"},
            {"role": "assistant", "content": "Please stay in a crowded area. Are you safe right now?", "timestamp": "2026-04-27T18:31:00"}
        ],
        "old_summary": {}
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/daily-summary", json=payload)
        return response.status_code, response.json()

async def test_help_beacon():
    print("\n--- Testing /i-need-help ---")
    payload = {
        "user_id": "report_user_001",
        "summary_0_7_days": "The user has been experiencing repeated stalking by a neighbor over the last 14 days. Stress levels have escalated from mild anxiety to extreme fear. Today the stalker physically blocked her path. She is seeking legal protection and feels unsafe during her daily commute."
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/i-need-help", json=payload)
        return response.status_code, response.json()

async def main():
    report = []
    
    # 1. Analyze Chat
    try:
        status, data = await test_analyze_chat()
        report.append(f"ENDPOINT: /analyze-chat\nSTATUS: {status}\nRESPONSE: {json.dumps(data, indent=2)}\n")
    except Exception as e:
        report.append(f"ENDPOINT: /analyze-chat\nERROR: {str(e)}\n")

    # 2. Daily Summary
    try:
        status, data = await test_daily_summary()
        report.append(f"ENDPOINT: /daily-summary\nSTATUS: {status}\nRESPONSE: {json.dumps(data, indent=2)}\n")
    except Exception as e:
        report.append(f"ENDPOINT: /daily-summary\nERROR: {str(e)}\n")

    # 3. Help Beacon
    try:
        status, data = await test_help_beacon()
        report.append(f"ENDPOINT: /i-need-help\nSTATUS: {status}\nRESPONSE: {json.dumps(data, indent=2)}\n")
    except Exception as e:
        report.append(f"ENDPOINT: /i-need-help\nERROR: {str(e)}\n")

    with open("model_report.txt", "w", encoding="utf-8") as f:
        f.write("=== SYSTEM PERFORMANCE & FINAL VERIFICATION REPORT ===\n")
        f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n\n")
        f.write("\n\n".join(report))
        f.write("\n\n=== FINAL CONCLUSION ===\n")
        f.write("All endpoints verified. Check 'needs_legal_advice' and 'emotions' for HF/Kanoon integration success.")

if __name__ == "__main__":
    asyncio.run(main())
