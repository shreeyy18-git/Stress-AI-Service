import os
from typing import Annotated, List, TypedDict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

from app.utils.prompts import CHAT_ANALYSIS_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    # add_messages is a reducer that appends new messages to the existing list
    messages: Annotated[List[BaseMessage], add_messages]
    user_info: str
    memory_summary: str
    legal_context: Optional[str] = ""

# ---------------------------------------------------------------------------
# Graph Logic
# ---------------------------------------------------------------------------

from langchain_core.runnables import RunnableConfig

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",       # Equivalent to Gemini 2 Flash
    "gemini-2.0-flash-lite",  # Equivalent to Gemini 2 Flash Lite
    "gemini-1.5-flash",       # Using 1.5 as 3 hasn't been released in Langchain yet
    "gemini-1.5-flash-8b",    # Using 1.5 as 3.1 hasn't been released in Langchain yet
]

def create_agent():
    async def call_model(state: AgentState):
        prompt = ChatPromptTemplate.from_messages([
            ("system", CHAT_ANALYSIS_SYSTEM_PROMPT + "\n\nUser Demographics:\n{user_info}\n\nUser Background:\n{memory_summary}\n\nLegal Context:\n{legal_context}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # Primary model from env
        primary_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        models_to_try = [primary_model_name] + [m for m in FALLBACK_MODELS if m != primary_model_name]

        # Get all configured API keys
        api_keys = []
        for key_name in ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3"]:
            val = os.getenv(key_name)
            if val:
                api_keys.append(val)
                
        if not api_keys:
             raise EnvironmentError("No GEMINI_API_KEY environment variables found.")

        last_exception = None
        # Try each key, and for each key, try the fallback models if needed.
        for api_key in api_keys:
            for model_name in models_to_try:
                try:
                    llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=api_key,
                        temperature=0.4,
                    )
                    chain = prompt | llm
                    
                    # We pass the full state context
                    response = await chain.ainvoke({
                        "messages": state["messages"],
                        "user_info": state["user_info"],
                        "memory_summary": state["memory_summary"],
                        "legal_context": state.get("legal_context") or "No legal context provided yet."
                    })
                    
                    return {"messages": [response]}
                except Exception as e:
                    # Log the failure and continue to the next model/key
                    print(f"Failed with key (ending '{api_key[-4:] if len(api_key)>4 else '...'}') and model {model_name}: {e}. Trying next...")
                    last_exception = e
        
        # If all keys and models fail, raise the last exception
        if last_exception:
            raise Exception(f"All API keys and fallback models failed. Last error: {last_exception}") from last_exception
        
        return {"messages": []}

    from app.services.kanoon_service import search_legal_context
    import json
    import re

    def _extract_json_from_msg(content: str):
        cleaned = re.sub(r"```(?:json)?", "", content).strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group())
        except:
            return {}

    async def legal_research(state: AgentState):
        """Node that calls Indian Kanoon if signaled."""
        last_msg = state["messages"][-1].content
        data = _extract_json_from_msg(last_msg)
        query = data.get("legal_query", "indian law")
        
        print(f"--- TRIGGERING LEGAL RESEARCH: {query} ---")
        context = await search_legal_context(query)
        
        return {"legal_context": context}

    def should_search_laws(state: AgentState):
        """Conditional edge logic."""
        last_msg = state["messages"][-1].content
        data = _extract_json_from_msg(last_msg)
        
        # Only search if triggered AND we haven't already fetched context
        if data.get("needs_legal_advice") is True and not state.get("legal_context"):
            return "research"
        return "end"

    # Build the graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", call_model)
    workflow.add_node("research", legal_research)

    workflow.add_edge(START, "agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_search_laws,
        {
            "research": "research",
            "end": END
        }
    )

    # After research, go back to agent for a final refined response
    workflow.add_edge("research", "agent")

    # Add memory persistence
    checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)

# Singleton instance
agent_app = create_agent()
