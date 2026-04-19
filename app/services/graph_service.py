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
            ("system", CHAT_ANALYSIS_SYSTEM_PROMPT + "\n\nUser Demographics:\n{user_info}\n\nUser Background:\n{memory_summary}"),
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
                        "memory_summary": state["memory_summary"]
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

    # Build the graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")

    workflow.add_edge("agent", END)

    # Add memory persistence
    checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)

# Singleton instance
agent_app = create_agent()
