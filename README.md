# 🧠 StressGuard AI: Stateful Emotional Support Microservice

StressGuard is a production-ready, highly resilient AI microservice built with **FastAPI**, **LangGraph**, and **Google Gemini**. It is designed to analyze user distress, provide empathetic grounding, and deliver context-aware legal support via the **Indian Kanoon** API.

The system features a state-of-the-art "Triple-Layer Failover" architecture, ensuring 100% uptime by dynamically switching between 5 different AI models and 3 distinct API keys during peak demand or outages.

---

## ✨ Key Features

### 🌈 Stateful Emotional Intelligence
- **Short-Term Memory**: Uses LangGraph and an in-memory `MemorySaver` to maintain high-fidelity context for continuous conversations.
- **Risk Assessment**: Classifies distress levels from `low` to `critical` with a safety-first conservative bias.
- **Multi-Label Emotions**: Detects complex emotional arcs (e.g., anxiety + helplessness).

### ⚖️ Smart Legal Support (Integrated Indian Kanoon)
- **Automatic Research**: If a user is in a high-risk situation or asks for help, the AI triggers an internal background search for Indian Central Acts and Rules.
- **Simplified Advice**: Translates complex legal citations into easy-to-understand, actionable advice while citing the specific Act or Law.

### 🛡️ Reliability & Resilience
- **Multi-Model Fallback**: Cycles through Gemini 2.5 Flash Lite → Gemini 2.0 Flash → Gemini 1.5 Flash to ensure a response never stops.
- **Triple API Key Rotation**: Automatically rotates through `GEMINI_API_KEY`, `GEMINI_API_KEY2`, and `GEMINI_API_KEY3` if rate limits are hit.

### 📊 Insightful Tracking
- **Cumulative Daily Summaries**: Generates high-quality 100-200 word psychiatric snapshots every day, maintaining a timestamped history.
- **Emergency Help Beacon**: Creates concise 2-4 line messages for the user's support system based on 7-day emotional trends.

---

## 🔬 High Precision & Anti-Hallucination

Unlike standard "one-pass" AI chatbots, StressGuard utilizes a **Multi-Node Agentic Architecture** to ensure the highest possible accuracy and eliminate hallucinations.

### 1. Multi-Pass Grounding
The system doesn't just "guess" an answer. It follows a structured LangGraph workflow:
- **Node A (Primary Analysis)**: Identifies emotional signals and specifically looks for legal/safety triggers.
- **Node B (External Validation)**: If a trigger is found, it fetches grounded facts from the **Indian Kanoon** API.
- **Node C (Refined Synthesis)**: A final agent merges original empathy with verified legal data, ensuring advice is based on actual laws, not model guesswork.

### 2. Strict Prompt Grounding
The engine uses **Strict Grounding Rules** which explicitly forbid the AI from inventing context, assuming hidden facts, or citing non-existent laws. If the AI is uncertain, it is programmed to choose the safer interpretation (higher risk) rather than fabricating reassurance.

### 3. Structured Data Validation
Every response is forced through a strict JSON schema. If the model output doesn't match the required structure or contains invalid formats, the system automatically detects the error and triggers a retry via the fallback models.

---

## 🏗️ Technical Stack

- **Backend Framework**: FastAPI (Async)
- **Orchestration**: LangGraph (Stateful Agentic Workflows)
- **AI Models**: Google Gemini (Flash & Lite series)
- **Data Retrieval**: Indian Kanoon API (Legal Context)
- **Server**: Gunicorn with Uvicorn workers (Production-grade)
- **Deployment**: Render-ready with `blueprint` configuration

---

## 🚀 API Documentation

### 1. Unified Chat Analysis
`POST /analyze-chat`
Analyzes distress, provides empathy, and integrates legal advice if needed.

**Request:**
```json
{
  "user_id": "0001",
  "message": "I feeling overwhelmed and someone is following me.",
  "user_info": "Female, 28, India",
  "history": [],
  "memory_summary": "User has previous anxiety issues."
}
```

**Response:**
```json
{
  "user_id": "0001",
  "emotions": ["fear", "paranoia"],
  "risk": "high",
  "stress_score": 85,
  "response": "I'm so sorry you're feeling this way. Under the Protection of Women from Domestic Violence Act, 2005...",
  "should_alert": true,
  "needs_legal_advice": true,
  "legal_query": "laws against stalking india"
}
```

### 2. Cumulative Daily Summary
`POST /daily-summary`
Aggregates a full day of chat into a deep psychological snapshot.

### 3. Help Beacon
`POST /i-need-help`
Generates a short emergency message for friends or family based on a 7-day trend.

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory:

```env
# Primary API Configuration
GEMINI_API_KEY="your_key_1"
GEMINI_API_KEY2="your_key_2"
GEMINI_API_KEY3="your_key_3"
GEMINI_MODEL="gemini-2.5-flash-lite"

# Third-Party Integrations
INDIAN_KANOON_API_KEY="your_kanoon_token"
```

---

## 🛠️ Local Development

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run Server**:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

3. **Explore Interactive Docs**:
Visit `http://127.0.0.1:8001/docs` for the Swagger UI.

---

## 🚢 Deployment (Render)

This repository includes a `render.yaml` file for instant deployment. 
1. Connect your GitHub repository to **Render**.
2. Create a new **Blueprint Instance**.
3. Add your `GEMINI_API_KEY` and `INDIAN_KANOON_API_KEY` in the Render dashboard environment settings.

---

## 📜 Safety Disclaimer
This service is an AI-powered conversational tool. It provides empathetic support and informational legal context. It is **not** a replacement for professional legal, medical, or emergency services. If you are in immediate danger, please contact your local emergency services directly.
